"""Saved chat history for logged-in customers (the `chat_messages` table).

Every function takes the user id from the verified login session (main.py),
never from anything typed in the chat, and every query filters on it, so a
customer can only read, extend or clear their own history.

Row format (one row per message):
    user_id, role ('user' | 'assistant'), content, created_at
    products_json: for assistant rows,
        {"product_ids": [...], "page_search": {...BrowseRequest} | null}
      Rows saved before this project store a JSON list of product objects;
      both formats are read.
"""

import json

from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart

import catalog
import privacy
from db import connect_rw
from models import BrowseRequest, ChatProduct

MODEL_HISTORY_MESSAGES = 20   # most recent saved messages sent to the model as context
UI_HISTORY_MESSAGES = 60      # most recent saved messages shown in the chat panel

def redact(text: str) -> str:
    """Remove card numbers and explicitly shared credentials (privacy.py) before a
    message is sent to the model, kept in memory or saved."""
    return privacy.redact(text)


def _parse_products_json(raw: str | None) -> tuple[list[str], dict | None]:
    if not raw:
        return [], None
    try:
        data = json.loads(raw)
    except ValueError:
        return [], None
    if isinstance(data, list):  # older rows: list of full product objects
        return [p["product_id"] for p in data if isinstance(p, dict) and "product_id" in p], None
    if isinstance(data, dict):
        return list(data.get("product_ids") or []), data.get("page_search")
    return [], None


def _rows(user_id: int, limit: int) -> list:
    with connect_rw() as conn:
        rows = conn.execute(
            """SELECT id, role, content, products_json, created_at FROM chat_messages
               WHERE user_id = ? ORDER BY id DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
    return list(reversed(rows))


def model_history(user_id: int) -> list[ModelMessage]:
    """The customer's recent saved conversation, in the form the agent expects."""
    rows = _rows(user_id, MODEL_HISTORY_MESSAGES)
    while rows and rows[0]["role"] != "user":  # start on a customer message
        rows = rows[1:]
    messages: list[ModelMessage] = []
    for r in rows:
        if r["role"] == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=r["content"])]))
        elif r["role"] == "assistant":
            messages.append(ModelResponse(parts=[TextPart(content=r["content"])]))
    return messages


def save_exchange(user_id: int, user_text: str, reply: str, product_ids: list[str], page_search: BrowseRequest | None) -> None:
    # Everything saved goes through the privacy filter, including the nested page-search fields.
    user_text, reply = privacy.redact(user_text), privacy.redact(reply)
    extra = json.dumps(privacy.redact_deep(
        {"product_ids": product_ids[:6], "page_search": page_search.model_dump() if page_search else None}))
    with connect_rw() as conn:  # one transaction: both rows or neither
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'user', ?, NULL)",
            (user_id, user_text),
        )
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
            (user_id, reply, extra),
        )


def ui_history(user_id: int) -> list[dict]:
    """Saved messages for the chat panel. Product cards are rebuilt from the
    current catalogue, so prices shown are today's, not a stale snapshot."""
    out = []
    with catalog.connect_ro() as conn:
        for r in _rows(user_id, UI_HISTORY_MESSAGES):
            ids, page_search = _parse_products_json(r["products_json"])
            cards = []
            for pid in dict.fromkeys(ids[:6]):
                row = catalog.get_product_row(conn, pid)
                if row is not None:
                    cards.append(ChatProduct(
                        product_id=row["product_id"], name=row["name"], price=row["price"],
                        image_url=catalog.image_url(row["image_file_path"]), url=catalog.product_url(row["product_id"]),
                        total_stock=row["total_stock"],
                    ).model_dump())
            out.append({
                "role": r["role"],
                "content": r["content"],
                "created_at": r["created_at"],
                # Older rows listed every product they mentioned; only show cards for short lists.
                "products": cards if len(ids) <= 6 else [],
                "page_search": page_search,
            })
    return out


def clear(user_id: int) -> int:
    with connect_rw() as conn:
        return conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,)).rowcount
