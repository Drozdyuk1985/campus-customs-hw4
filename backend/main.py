"""Campus Customs HW4 - FastAPI backend.

Serves the real product catalogue, stock levels and product images from the
supplied SQLite database, account sign-up, login and logout (auth.py), and
the shopping-assistant chat (agent.py). Product routes use a read-only
connection; only auth.py writes, to the users and sessions tables.

Run from the backend folder (with the hw4 virtual environment active):
    uvicorn main:app --reload --port 8000
"""

import json
import logging
import re
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from urllib.parse import parse_qs, urlsplit

from fastapi import Cookie, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic_ai.exceptions import UsageLimitExceeded

import agent
import auth
import catalog
import chat_store
import privacy
from db import PRODUCTS_DIR, connect_ro
from models import (
    BrowseRequest, ChatHistory, ChatOption, ChatProduct, ChatRequest, ChatResponse, PageContext, PageSearchResults,
    ProductDetail,
    ProductSummary, ShopDeps, ViewedProduct,
)

log = logging.getLogger("campus_customs")

@asynccontextmanager
async def lifespan(_: FastAPI):
    auth.ensure_sessions_table()
    yield


app = FastAPI(title="Campus Customs HW4", lifespan=lifespan)
app.include_router(auth.router)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    # FastAPI's default 422 echoes the submitted values back, which would include
    # passwords. Return only which field was wrong.
    fields = [str(e["loc"][-1]) for e in exc.errors() if e.get("loc")]
    return JSONResponse(status_code=422, content={"detail": f"Please check these fields: {', '.join(fields) or 'request'}."})


@app.get("/api/health")
def health() -> dict:
    with connect_ro() as conn:
        count = conn.execute("SELECT COUNT(*) FROM catalogue").fetchone()[0]
    return {"status": "ok", "products": count, "assistant": agent.config_status()}


@app.get("/api/categories")
def categories() -> list[str]:
    return catalog.CATEGORIES


@app.get("/api/products", response_model=list[ProductSummary])
def list_products(
    q: str | None = Query(None, max_length=100, description="Search name, description, colours and tags"),
    category: str | None = Query(None, description="One of /api/categories"),
    min_price: float | None = Query(None, ge=0, description="Lowest price, inclusive"),
    max_price: float | None = Query(None, ge=0, description="Highest price, inclusive"),
    size: str | None = Query(None, description="Only products with this size in stock (XS, S, M, L, XL, XXL)"),
    sort: str = Query("name", pattern="^(name|price_low_to_high|price_high_to_low)$"),
) -> list[dict]:
    sql = catalog.PRODUCT_SELECT
    params: list[str] = []
    if q and q.strip():
        sql += " WHERE (c.name || ' ' || c.description || ' ' || c.colors || ' ' || c.search_tags) LIKE ?"
        params.append(f"%{q.strip()}%")
    sql += " GROUP BY c.product_id ORDER BY c.name"
    with connect_ro() as conn:
        rows = conn.execute(sql, params).fetchall()
    products = [catalog.summary_from_row(r) for r in rows]
    if category:
        products = [p for p in products if p["category"] == category]
    if min_price is not None:
        products = [p for p in products if p["price"] >= min_price]
    if max_price is not None:
        products = [p for p in products if p["price"] <= max_price]
    if size:
        wanted = catalog.normalize_size(size)
        products = [p for p in products if wanted in p["sizes_in_stock"]] if wanted else []
    if sort != "name":
        products.sort(key=lambda p: (p["price"], p["name"]), reverse=sort == "price_high_to_low")
    return products


@app.get("/api/products/{product_id}", response_model=ProductDetail)
def get_product(product_id: str) -> dict:
    with connect_ro() as conn:
        row = catalog.get_product_row(conn, product_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        inventory = catalog.size_stock(conn, product_id)
    return {
        **catalog.summary_from_row(row),
        "description": row["description"],
        "search_tags": json.loads(row["search_tags"]),
        "inventory": inventory,
    }


# ---------------------------------------------------------------- chat

CHAT_MESSAGES_PER_MINUTE = 12
_chat_times: dict[str, deque] = defaultdict(deque)


def _chat_rate_limited(key: str) -> bool:
    times = _chat_times[key]
    now = time.monotonic()
    while times and now - times[0] > 60:
        times.popleft()
    if len(times) >= CHAT_MESSAGES_PER_MINUTE:
        return True
    times.append(now)
    return False


def describe_page(page: PageContext | None) -> tuple[str, ViewedProduct | None]:
    """Turn the browser's current address into a short description for the agent.

    The address is only a hint about what the customer is looking at. A product
    ID in it is checked against the catalogue before the agent hears about it.
    """
    if page is None:
        return "unknown page", None
    url = urlsplit(page.path)
    path, query = url.path.rstrip("/") or "/", parse_qs(url.query)
    if m := re.fullmatch(r"/products/([a-z0-9-]{1,120})", path):
        with connect_ro() as conn:
            row = catalog.get_product_row(conn, m.group(1))
        if row is None:
            return "a product page for a product that doesn't exist", None
        return f'the product page for "{row["name"]}"', ViewedProduct(product_id=row["product_id"], name=row["name"])
    if path == "/products":
        filters = []
        if (c := query.get("category", [""])[0]) in catalog.CATEGORIES:
            filters.append(f"category {c}")
        if q := query.get("q", [""])[0][:60]:
            filters.append(f'search "{q}"')
        return "the Products page" + (f" filtered by {', '.join(filters)}" if filters else " (all products)"), None
    names = {"/": "the Home page", "/about": "the About Us page", "/login": "the Log in page",
             "/create-account": "the Create account page"}
    return names.get(path, "another page of the site"), None


@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request, cc_session: str | None = Cookie(None)) -> dict:
    # Who the customer is comes only from the login cookie, never from the message text.
    user = auth.current_user(cc_session)
    owner = f"user:{user['id']}" if user else f"guest:{request.client.host if request.client else '?'}"
    if _chat_rate_limited(owner):
        raise HTTPException(429, "You're sending messages quickly. Please wait a moment and try again.")
    page_description, viewed = describe_page(body.page)
    deps = ShopDeps(
        customer_name=f"{user['first_name']} {user['last_name']}".strip() if user else None,
        customer_first_name=user["first_name"] if user else None,
        customer_email=user["email"] if user else None,
        page_description=page_description,
        viewed_product=viewed,
    )
    # Card numbers and explicitly shared credentials are removed before the message
    # reaches the model, guest memory, saved history or the audit trail (privacy.py).
    message = privacy.redact(body.message.strip())
    saved_history = chat_store.model_history(user["id"]) if user else None
    try:
        conversation_id, out = await agent.chat(message, body.conversation_id, owner, deps, saved_history)
    except agent.AssistantNotConfigured as e:
        raise HTTPException(503, str(e))
    except UsageLimitExceeded:
        log.warning("chat: usage limit reached")
        raise HTTPException(502, "That question took too many steps for me. Could you ask it a simpler way?")
    except agent.RunTimedOut:
        log.warning("chat: run timed out")
        raise HTTPException(504, "That took too long to answer. Please try again, or ask a simpler question.")
    except Exception as e:  # model/network errors: log the type and status only, never the key or the request
        log.error("chat: model call failed (%s %s)", type(e).__name__, getattr(e, "status_code", ""))
        raise HTTPException(502, "Sorry, I'm having trouble answering right now. Please try again in a moment.")

    search_results = page_search(out.show_on_page) if out.show_on_page else None
    product_ids = [] if search_results else out.product_ids
    # Saved for logged-in customers only. Messages blocked by the provider's filter
    # aren't saved, so they can't be re-sent (and re-blocked) as history next time.
    saved = bool(user) and out is not agent.FILTERED_REPLY
    if saved:
        chat_store.save_exchange(user["id"], message, out.reply, product_ids, out.show_on_page)
    return {
        "conversation_id": conversation_id,
        "reply": out.reply,
        # Browsing results go on the page, so the small in-chat cards aren't repeated.
        "products": chat_products(product_ids),
        "search_results": search_results,
        "options": chat_options(out.clarify_options),
        "saved": saved,
    }


@app.get("/api/chat/history", response_model=ChatHistory)
def chat_history(cc_session: str | None = Cookie(None)) -> dict:
    """The logged-in customer's own saved messages. Guests have no saved history."""
    user = auth.current_user(cc_session)
    if user is None:
        raise HTTPException(401, "Log in to see your saved chat history.")
    return {"messages": chat_store.ui_history(user["id"])}


@app.delete("/api/chat/history")
def clear_chat_history(cc_session: str | None = Cookie(None)) -> dict:
    user = auth.current_user(cc_session)
    if user is None:
        raise HTTPException(401, "Log in to manage your chat history.")
    return {"deleted": chat_store.clear(user["id"])}


@app.post("/api/page-search", response_model=PageSearchResults)
def page_search_route(body: BrowseRequest) -> PageSearchResults:
    """Re-show a saved browse request's results (e.g. from chat history). Catalogue only."""
    return page_search(body)


PAGE_RESULTS_LIMIT = 48  # the largest category has 29 products


def page_search(req: BrowseRequest) -> PageSearchResults:
    """Run the agent's browse request against the catalogue, with the same search the agent's tool uses."""
    category = req.category if req.category in catalog.CATEGORIES else None
    with connect_ro() as conn:
        size = catalog.normalize_size(req.size_in_stock) if req.size_in_stock else None
        rows, exact = catalog.search(conn, req.query, category, req.max_price, req.sort, size)
    products = [catalog.summary_from_row(r) for r in rows[:PAGE_RESULTS_LIMIT]]
    return PageSearchResults(
        title=req.title.strip()[:80] or "Search results",
        query=req.query, category=category, max_price=req.max_price, sort=req.sort, size_in_stock=size,
        total=len(products), exact=exact, products=products,
    )


def chat_options(product_ids: list[str]) -> list[ChatOption]:
    """Tappable choices for a follow-up question, checked against the catalogue (unknown IDs are dropped)."""
    options = []
    with connect_ro() as conn:
        for pid in dict.fromkeys(product_ids[:5]):
            row = catalog.get_product_row(conn, pid)
            if row is not None:
                summary = catalog.summary_from_row(row)
                options.append(ChatOption(product_id=pid, name=row["name"], price=row["price"],
                                          image_url=summary["image_url"], sizes_in_stock=summary["sizes_in_stock"]))
    return options


def chat_products(product_ids: list[str]) -> list[ChatProduct]:
    """Product cards for the reply, looked up fresh from the database.

    The model only names product IDs; names, prices and images always come from
    the catalogue, and IDs that don't exist are dropped.
    """
    cards = []
    with connect_ro() as conn:
        for pid in dict.fromkeys(product_ids[:6]):
            row = catalog.get_product_row(conn, pid)
            if row is not None:
                cards.append(ChatProduct(
                    product_id=row["product_id"], name=row["name"], price=row["price"],
                    image_url=catalog.image_url(row["image_file_path"]), url=catalog.product_url(row["product_id"]),
                    total_stock=row["total_stock"],
                ))
    return cards


# Product photos: /media/products/<file>.jpg. Uses the white-background display
# copies from prepare_images.py (data/products_web/) when all are present,
# otherwise the supplied photos in data/products/.
_web = PRODUCTS_DIR.parent / "products_web"
IMAGE_DIR = _web if _web.is_dir() and len(list(_web.glob("*.jpg"))) >= len(list(PRODUCTS_DIR.glob("*.jpg"))) else PRODUCTS_DIR
if IMAGE_DIR == PRODUCTS_DIR:
    log.warning("Serving original product photos; run `python prepare_images.py` for consistent white backgrounds.")
app.mount("/media/products", StaticFiles(directory=IMAGE_DIR), name="product-images")
