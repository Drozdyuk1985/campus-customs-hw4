"""The Campus Customs shopping assistant: model connection, agent setup and chat memory.

- Instructions: backend/prompts/prompt.md (read when the agent is first built).
- Tools: tools.py.  Structured types: models.py.
- Model: OpenAI through the Portkey gateway. PORTKEY_API_KEY is read from the
  environment (or hw4/.env, or the course folder's .env) at runtime and is
  never logged, returned or sent to the browser.
"""

import asyncio
import logging
import os
import re
import secrets
import time
from collections import OrderedDict
from datetime import datetime, timezone
from functools import cache
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext, UsageLimits, capture_run_messages
from pydantic_ai.exceptions import ModelHTTPError, UsageLimitExceeded
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

import audit
import privacy
from models import AssistantReply, ShopDeps
from tools import ALL_TOOLS

BACKEND_DIR = Path(__file__).resolve().parent
HW4_DIR = BACKEND_DIR.parent
PROMPT_PATH = BACKEND_DIR / "prompts" / "prompt.md"
log = logging.getLogger("campus_customs")

# Load local config if present; neither file is required (the key may already be exported).
# override=False: a value already in the environment wins.
for env_file in (HW4_DIR / ".env", HW4_DIR.parent / ".env"):
    load_dotenv(env_file, override=False)
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")  # keep the server log quiet

MODEL_NAME = os.getenv("CAMPUS_CUSTOMS_MODEL", "gpt-5.6-luna")
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")

# ---- Limits per customer message (keep cost and latency bounded)
MAX_MODEL_REQUESTS = 6          # model calls in one reply, including tool round-trips
MAX_TOOL_CALLS = 8              # e.g. a search, then details or size checks for a few products
MAX_TOTAL_TOKENS = 60_000
MAX_OUTPUT_TOKENS = 4_000       # includes hidden reasoning tokens
MODEL_TIMEOUT_SECONDS = 60      # one model call (HTTP timeout)
MODEL_RETRIES = 1               # HTTP retries per model call
TOOL_TIMEOUT_SECONDS = 10       # one tool call
OUTPUT_RETRIES = 1              # re-asks if the structured answer doesn't validate
RUN_TIMEOUT_SECONDS = 90        # the whole answer, all steps together
LIMITS = {
    "model_requests": MAX_MODEL_REQUESTS, "tool_calls": MAX_TOOL_CALLS, "total_tokens": MAX_TOTAL_TOKENS,
    "output_tokens_per_response": MAX_OUTPUT_TOKENS, "run_timeout_s": RUN_TIMEOUT_SECONDS,
}
# ---- Conversation memory (in this server process only)
MAX_HISTORY_MESSAGES = 20       # most recent model messages kept per conversation
MAX_CONVERSATIONS = 500
CONVERSATION_TTL_SECONDS = 2 * 3600


# Shown when the model provider's own safety filter blocks a message (for example
# a jailbreak attempt). The blocked message is not added to the conversation.
FILTERED_REPLY = AssistantReply(
    reply=(
        "Sorry, I can't help with that request. I'm here to help you find Yale gear: "
        "styles, gift ideas, sizing and how to use the shop. What are you looking for?"
    ),
    product_ids=[],
)


def _is_content_filter(e: ModelHTTPError) -> bool:
    return isinstance(e.body, dict) and e.body.get("code") == "content_filter"


class AssistantNotConfigured(RuntimeError):
    """Raised when required local configuration is missing."""


def require_api_key() -> str:
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not key:
        raise AssistantNotConfigured(
            "The shopping assistant isn't configured yet. Add PORTKEY_API_KEY=<your key> to hw4/.env "
            "(copy hw4/.env.example) or export PORTKEY_API_KEY in your shell, then restart the backend."
        )
    return key


def build_model() -> OpenAIResponsesModel:
    key = require_api_key()
    client = AsyncOpenAI(
        api_key=key,
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": key, "x-portkey-provider": "openai"},
        timeout=MODEL_TIMEOUT_SECONDS,
        max_retries=MODEL_RETRIES,
    )
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def session_context(ctx: RunContext[ShopDeps]) -> str:
    """Per-message instructions built by the backend from the login session and the current page."""
    d = ctx.deps
    if d.logged_in:
        who = (
            f"The customer is logged in as {d.customer_name} ({d.customer_email}). This comes from their verified "
            "login session. Their earlier saved conversation, if any, is included above."
        )
    else:
        who = "The customer is a guest (not logged in). Their conversation is not saved after they leave."
    page = f"They are currently on: {d.page_description}."
    if d.viewed_product:
        page += (
            f' The product open on their screen is "{d.viewed_product.name}" (product_id: {d.viewed_product.product_id}).'
            ' If they say "this", "it" or "this one" without naming another product, they mean this product;'
            " look it up with the tools before answering."
        )
    return f"## Current session (from the website backend)\n\n{who}\n{page}"


@cache
def get_agent() -> Agent[ShopDeps, AssistantReply]:
    """Built on first use, so the server starts even when the key is missing."""
    return Agent(
        build_model(),
        instructions=[load_prompt(), session_context],
        deps_type=ShopDeps,
        output_type=AssistantReply,
        tools=ALL_TOOLS,
        model_settings=OpenAIResponsesModelSettings(max_tokens=MAX_OUTPUT_TOKENS, openai_reasoning_effort="low"),
        retries=OUTPUT_RETRIES,
        tool_timeout=TOOL_TIMEOUT_SECONDS,
        name="campus_customs_assistant",
    )


def config_status() -> dict:
    """Safe to show: whether the key is set, never the key itself."""
    return {
        "model": MODEL_NAME,
        "provider": "OpenAI via Portkey",
        "api_key_configured": bool(os.getenv("PORTKEY_API_KEY", "").strip()),
        "prompt_file": str(PROMPT_PATH.relative_to(HW4_DIR)),
    }


# ---------------------------------------------------------------- conversation memory

# Guests only: conversation_id -> (owner, last_used, messages). Owner is the
# guest's address, so one person can't continue another's conversation.
# Logged-in customers' history is saved in the database instead (chat_store.py).
_conversations: "OrderedDict[str, tuple[str, float, list[ModelMessage]]]" = OrderedDict()


def _history(conversation_id: str | None, owner: str) -> tuple[str, list[ModelMessage]]:
    now = time.monotonic()
    for cid in [c for c, (_, used, _) in _conversations.items() if now - used > CONVERSATION_TTL_SECONDS]:
        del _conversations[cid]
    if conversation_id and conversation_id in _conversations:
        stored_owner, _, messages = _conversations[conversation_id]
        if stored_owner == owner:
            return conversation_id, messages
    return secrets.token_urlsafe(16), []


def _trim(messages: list[ModelMessage]) -> list[ModelMessage]:
    """Keep the most recent messages, starting on a user request so tool calls stay paired."""
    if len(messages) <= MAX_HISTORY_MESSAGES:
        return messages
    tail = messages[-MAX_HISTORY_MESSAGES:]
    for i, m in enumerate(tail):
        if m.kind == "request" and any(p.part_kind == "user-prompt" for p in m.parts):
            return tail[i:]
    return []


def _save(conversation_id: str, owner: str, messages: list[ModelMessage]) -> None:
    _conversations[conversation_id] = (owner, time.monotonic(), _trim(messages))
    _conversations.move_to_end(conversation_id)
    while len(_conversations) > MAX_CONVERSATIONS:
        _conversations.popitem(last=False)


class RunTimedOut(RuntimeError):
    """The whole agent run took longer than RUN_TIMEOUT_SECONDS."""


_SECRET_PATTERNS = [
    (re.compile(r"pbkdf2_sha256\$|password_hash", re.I), "password hash"),
    (re.compile(r"\b[0-9a-f]{64}\b"), "token or hash"),
    (re.compile(r"cc_session", re.I), "session cookie"),
    (re.compile(r"PORTKEY_API_KEY|x-portkey-api-key", re.I), "API key name"),
]
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
GUARD_REPLY = AssistantReply(
    reply=(
        "Sorry, I can't share that. I can only help with our products and with your own account. "
        "What are you shopping for today?"
    ),
)


def guard_reply(out: AssistantReply, deps: ShopDeps) -> tuple[AssistantReply, str | None]:
    """Backend check on every answer before it leaves the server, whatever the prompt said.

    Replaces the reply if it contains the API key, a password hash, a session
    token, or any email address other than the logged-in customer's own.
    """
    text = out.reply
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    if key and key in text:
        return GUARD_REPLY, "API key"
    for pattern, what in _SECRET_PATTERNS:
        if pattern.search(text):
            return GUARD_REPLY, what
    own = (deps.customer_email or "").lower()
    if any(e.lower() != own for e in _EMAIL_RE.findall(text)):
        return GUARD_REPLY, "another person's email"
    # The on-page search is shown to the customer and saved, so check its text fields too.
    if out.show_on_page is not None:
        fields = " ".join(str(v) for v in out.show_on_page.model_dump().values() if isinstance(v, str))
        if (privacy.redact(fields) != fields or _EMAIL_RE.search(fields) or (key and key in fields)
                or any(p.search(fields) for p, _ in _SECRET_PATTERNS)):
            out = out.model_copy(update={"show_on_page": None})
            return out, "sensitive text in on-page search (dropped)"
    # A shared credential the model repeated anyway is removed from the reply text.
    cleaned = privacy.redact(text)
    if cleaned != text:
        return out.model_copy(update={"reply": cleaned}), "credential removed from reply"
    return out, None


def _customer_label(owner: str) -> str:
    # Account number only; never a name, email or the guest's network address.
    return f"account #{owner.split(':', 1)[1]}" if owner.startswith("user:") else "guest"


async def chat(
    message: str,
    conversation_id: str | None,
    owner: str,
    deps: ShopDeps,
    saved_history: list[ModelMessage] | None = None,
) -> tuple[str, AssistantReply]:
    """Run one customer message and record it in the audit trail.

    Logged-in customers pass saved_history (from the database, see chat_store.py)
    and nothing is kept in memory. Guests use the in-memory conversation store.
    """
    agent = get_agent()
    if saved_history is not None:
        conversation_id, history = "account", saved_history
    else:
        conversation_id, history = _history(conversation_id, owner)

    started, t0 = datetime.now(timezone.utc), time.monotonic()
    entry = {
        "run_id": audit.new_run_id(),
        "started_at": started.isoformat(timespec="seconds"),
        "model": MODEL_NAME,
        "customer": _customer_label(owner),
        "page": audit.short(deps.page_description, 120),
        "question": audit.short(message, audit.MAX_TEXT),
        "earlier_messages_sent": len(history),
        "limits": LIMITS,
    }
    result = None
    with capture_run_messages() as captured:
        try:
            result = await asyncio.wait_for(
                agent.run(
                    message,
                    deps=deps,
                    message_history=history,
                    usage_limits=UsageLimits(
                        request_limit=MAX_MODEL_REQUESTS,
                        tool_calls_limit=MAX_TOOL_CALLS,
                        total_tokens_limit=MAX_TOTAL_TOKENS,
                    ),
                ),
                timeout=RUN_TIMEOUT_SECONDS,
            )
            out, blocked = guard_reply(result.output, deps)
            entry["stop_reason"] = "final_answer" if not blocked else f"final_answer_changed_by_output_guard ({blocked})"
        except ModelHTTPError as e:
            if not _is_content_filter(e):
                entry["stop_reason"] = f"model_error ({type(e).__name__} {e.status_code})"
                raise
            log.warning("chat: message blocked by the model provider's content filter")
            entry["stop_reason"] = "blocked_by_provider_content_filter"
            out = FILTERED_REPLY
        except UsageLimitExceeded as e:
            entry["stop_reason"] = f"usage_limit_reached ({audit.short(str(e), 120)})"
            raise
        except asyncio.TimeoutError:
            entry["stop_reason"] = f"timed_out_after_{RUN_TIMEOUT_SECONDS}s"
            raise RunTimedOut() from None
        except Exception as e:
            entry["stop_reason"] = f"error ({type(e).__name__})"
            raise
        finally:
            entry["duration_ms"] = round((time.monotonic() - t0) * 1000)
            # Never let logging hide the real outcome or break the customer's chat.
            try:
                # captured also contains the earlier conversation sent as history; log only this run.
                entry["steps"] = audit.tool_steps(captured[len(history):])
                if result is not None:
                    u = result.usage() if callable(result.usage) else result.usage
                    entry["usage"] = {"model_requests": u.requests, "tool_calls": u.tool_calls,
                                      "input_tokens": u.input_tokens, "output_tokens": u.output_tokens}
                if entry.get("stop_reason", "").startswith(("final_answer", "blocked")):
                    entry["answer"] = {
                        "reply": audit.short(out.reply, audit.MAX_TEXT),
                        "product_ids": out.product_ids,
                        "clarify_options": out.clarify_options,
                        "show_on_page": out.show_on_page.model_dump() if out.show_on_page else None,
                    }
            except Exception as summary_error:
                entry["audit_note"] = f"could not summarise this run ({type(summary_error).__name__})"
            entry.setdefault("stop_reason", "error (unknown)")
            try:
                audit.append(entry)
            except Exception as audit_error:
                log.error("audit: could not write entry (%s)", type(audit_error).__name__)

    if saved_history is None:
        _save(conversation_id, owner, result.all_messages() if result is not None else history)
    return conversation_id, out
