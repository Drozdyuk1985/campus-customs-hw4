"""Append-only audit trail of the shopping assistant's real activity.

Every chat handled by POST /api/chat adds one entry to output/audit_trail.json:
when it ran, who asked (account number or "guest", never a name or email),
a short redacted preview of the question, each tool the agent called with
short arguments and a short result, the reason the run stopped, usage
counts, and a short summary of the answer.

Rules:
- Append only. Existing entries are read and written back unchanged; nothing
  is ever deleted or rewritten. If the file can't be read as JSON, it is
  renamed aside (kept, not deleted) and a new file is started.
- Writes are atomic (temporary file, then rename) and locked, so two requests
  finishing together can't lose an entry.
- Privacy: every string in a new entry, nested fields included, goes through
  scrub() just before writing. scrub() removes card-like numbers and explicitly
  shared credentials (privacy.py), the API key value, password hashes,
  64-character hex tokens, session cookie values, emails and registered
  customers' full names. Pattern-based: see output/harness.md for limits. Only product-tool data and short
  text previews are logged, and every string passes through scrub() first.
"""

import json
import os
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import fcntl  # file locking for the audit trail; available on macOS and Linux only
except ImportError as e:  # pragma: no cover - Windows
    raise ImportError(
        "The Campus Customs backend supports macOS and Linux. It uses fcntl file locking for the "
        "audit trail, which Windows doesn't provide (see README: 'Supported setup')."
    ) from e
from pydantic import BaseModel
import privacy
from pydantic_ai.messages import ModelMessage, ModelResponse, RetryPromptPart, ToolCallPart, ToolReturnPart

HW4_DIR = Path(__file__).resolve().parent.parent
AUDIT_PATH = Path(os.getenv("CAMPUS_CUSTOMS_AUDIT", HW4_DIR / "output" / "audit_trail.json"))
LOCK_PATH = AUDIT_PATH.with_suffix(".lock")

MAX_TEXT = 160        # characters kept from a question or answer
MAX_ARGS = 200        # characters kept from tool arguments
MAX_RESULT = 240      # characters kept from a tool result summary

_lock = threading.Lock()

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_SECRETISH = re.compile(r"pbkdf2_sha256\$\S+|\bcc_session=\S+|\bsk-[A-Za-z0-9_-]{8,}|\b[0-9a-f]{64}\b", re.I)


def _customer_names() -> list[str]:
    """Full names of registered customers, so a name typed into the chat isn't logged."""
    try:
        from db import connect_ro
        with connect_ro() as conn:
            rows = conn.execute("SELECT name, first_name, last_name FROM users").fetchall()
    except Exception:
        return []
    names = {r["name"] for r in rows if r["name"]} | {f"{r['first_name']} {r['last_name']}" for r in rows if r["first_name"] and r["last_name"]}
    return sorted((n for n in names if " " in n.strip()), key=len, reverse=True)


def scrub(text: str) -> str:
    """Remove anything secret or personal from a string before it is logged."""
    text = privacy.redact(text)  # card numbers and explicitly shared credentials
    for name in _customer_names():
        text = re.sub(re.escape(name), "[customer name removed]", text, flags=re.I)
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    if key and key in text:
        text = text.replace(key, "[api key removed]")
    text = _SECRETISH.sub("[secret removed]", text)
    text = _CARD.sub("[card number removed]", text)
    return _EMAIL.sub("[email removed]", text)


def short(value, limit: int) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    text = scrub(" ".join(text.split()))
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _summarize_result(tool: str, content) -> str:
    """Readable one-line summaries for the product tools; short JSON otherwise."""
    data = content.model_dump(mode="json") if isinstance(content, BaseModel) else content
    try:
        if tool == "search_products":
            names = ", ".join(p["name"] for p in data["products"][:4])
            more = "…" if data["total_matches"] > 4 else ""
            return short(f"{data['total_matches']} matches (exact={data['all_words_matched']}, "
                         + (f"${data['lowest_price']:.2f}–${data['highest_price']:.2f}" if data["total_matches"] else "no prices")
                         + f"): {names}{more}", MAX_RESULT)
        if tool == "get_product_details" and data.get("found"):
            sizes = ", ".join(f"{s['size']}={s['quantity']}" for s in data["sizes"])
            return short(f"{data['name']} ${data['price']:.2f}; {sizes}", MAX_RESULT)
        if tool == "check_size_stock" and data.get("found") and data.get("size"):
            return short(f"{data['name']} {data['size']}: {data['quantity']} ({data['status']}); "
                         f"other sizes in stock: {', '.join(data['other_sizes_in_stock']) or 'none'}", MAX_RESULT)
        if tool == "find_alternatives" and data.get("found"):
            alts = "; ".join(f"{a['name']} (${a['price']:.2f}, {data.get('requested_size') or 'any'}="
                             f"{a['requested_size_quantity'] if a['requested_size_quantity'] is not None else 'in stock'})"
                             for a in data["alternatives"])
            return short(f"{data['name']} {data.get('requested_size') or ''} {data.get('requested_size_status') or ''}; "
                         f"alternatives: {alts or 'none'}", MAX_RESULT)
    except (KeyError, TypeError):
        pass
    return short(data, MAX_RESULT)


def tool_steps(messages: list[ModelMessage]) -> list[dict]:
    """The tool calls in a run, paired with their results, in order."""
    calls, results, steps = {}, {}, []
    for m in messages:
        for p in m.parts:
            if isinstance(p, ToolCallPart):
                calls[p.tool_call_id] = p
            elif isinstance(p, ToolReturnPart):
                results[p.tool_call_id] = p
            elif isinstance(p, RetryPromptPart) and p.tool_call_id:
                results[p.tool_call_id] = p
    for m in messages:
        if not isinstance(m, ModelResponse):
            continue
        for p in m.parts:
            if not isinstance(p, ToolCallPart) or p.tool_name == "final_result":
                continue  # final_result is how the structured answer is returned, not a lookup
            r = results.get(p.tool_call_id)
            if isinstance(r, ToolReturnPart):
                result = _summarize_result(p.tool_name, r.content)
            elif isinstance(r, RetryPromptPart):
                result = "retry requested: " + short(r.content, MAX_RESULT)
            else:
                result = "no result (run stopped first)"
            steps.append({
                "step": len(steps) + 1,
                "time": (p_time := getattr(m, "timestamp", None)) and p_time.isoformat(timespec="seconds"),
                "tool": p.tool_name,
                "args": short(p.args_as_dict(), MAX_ARGS),
                "result": result,
            })
    return steps


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + secrets.token_hex(3)


def _read_all() -> list:
    if not AUDIT_PATH.exists():
        return []
    try:
        data = json.loads(AUDIT_PATH.read_text(encoding="utf-8") or "[]")
        if isinstance(data, list):
            return data
    except ValueError:
        pass
    # Unreadable: keep it under another name rather than overwrite it.
    AUDIT_PATH.rename(AUDIT_PATH.with_name(f"audit_trail.unreadable-{int(time.time())}.json"))
    return []


def scrub_deep(value):
    """scrub() every string inside an entry, however deeply nested (e.g. answer.show_on_page.title)."""
    if isinstance(value, str):
        return scrub(value)
    if isinstance(value, dict):
        return {k: scrub_deep(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [scrub_deep(v) for v in value]
    return value


def append(entry: dict) -> None:
    """Add one entry to the end of the trail without changing earlier entries.

    The new entry is scrubbed as a whole first, so no field can skip the privacy
    filter. Existing entries are written back exactly as they were.
    """
    entry = scrub_deep(entry)
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock, open(LOCK_PATH, "w") as lockf:
        fcntl.flock(lockf, fcntl.LOCK_EX)  # also guards against a second server process
        entries = _read_all()
        entries.append(entry)
        tmp = AUDIT_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, AUDIT_PATH)
