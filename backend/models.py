"""Structured types for the API and the shopping assistant."""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------- products

class SizeStock(BaseModel):
    size: str
    quantity: int


class ProductSummary(BaseModel):
    product_id: str
    name: str
    garment_type: str
    category: str
    short_description: str
    colors: list[str]
    price: float
    image_url: str
    total_stock: int
    sizes_in_stock: list[str]


class ProductDetail(ProductSummary):
    description: str
    search_tags: list[str]
    inventory: list[SizeStock]


# ---------------------------------------------------------------- accounts

MAX_PASSWORD = 128


class SignupRequest(BaseModel):
    first_name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    email: str = Field(max_length=254)
    password: str = Field(max_length=MAX_PASSWORD)
    confirm_password: str = Field(max_length=MAX_PASSWORD)


class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=MAX_PASSWORD)


class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str


# ---------------------------------------------------------------- chat

MAX_CHAT_MESSAGE = 1000


class PageContext(BaseModel):
    """Where the customer is on the website when they send a message (sent by the browser)."""

    path: str = Field("/", max_length=300, description='Current address, e.g. "/products/morse-1-4-zip" or "/products?category=Hoodies".')


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_CHAT_MESSAGE)
    # Guests only: returned by the previous reply; omit to start a new conversation.
    # Logged-in customers' conversations are found from their login session instead.
    conversation_id: str | None = Field(None, max_length=64)
    page: PageContext | None = None


SortOrder = Literal["relevance", "price_low_to_high", "price_high_to_low"]


class BrowseRequest(BaseModel):
    """Ask the website to show a set of search results as product cards on the page."""

    query: str = Field(description='The same search words used with search_products, e.g. "hoodie", "saybrook". "" for category/price only.')
    category: str | None = Field(None, description="Optional: T-Shirts, Long Sleeves, Crewnecks, Hoodies, Quarter-Zips or Jackets & Fleece.")
    max_price: float | None = Field(None, description="Optional highest price in US dollars.")
    sort: SortOrder = "relevance"
    size_in_stock: str | None = Field(None, description="Optional size; only products with that size in stock are shown.")
    title: str = Field(description='Short heading for the results on the page, e.g. "Hoodies" or "Saybrook gear under $60".')


class AssistantReply(BaseModel):
    """What the agent must return for every message."""

    reply: str = Field(description="The message shown to the customer. Plain text, friendly, at most about 150 words.")
    product_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Up to 6 product_id values (exactly as returned by the tools) of the products this reply recommends "
            "or talks about, most relevant first. Empty when no specific product is discussed, and empty when "
            "show_on_page is used."
        ),
    )
    clarify_options: list[str] = Field(
        default_factory=list,
        description=(
            "When the customer's question could mean several products, the product_id values (from tool results) "
            "of up to 5 real candidates. The website shows them as tappable choices under your follow-up question."
        ),
    )
    show_on_page: BrowseRequest | None = Field(
        None,
        description=(
            "Set when the customer wants to browse or see a set of products (e.g. 'what hoodies do you have?'). "
            "The website runs this search on the catalogue and shows the results as product cards on the page."
        ),
    )


class ChatProduct(BaseModel):
    """A product card shown under a chat reply. Built from the database, not from the model."""

    product_id: str
    name: str
    price: float
    image_url: str
    url: str
    total_stock: int


class ChatOption(BaseModel):
    """A tappable choice under a follow-up question. Built from the database, not from the model."""

    product_id: str
    name: str
    price: float
    image_url: str
    sizes_in_stock: list[str]


class PageSearchResults(BaseModel):
    """Search results for the page, run by the server from the agent's BrowseRequest."""

    title: str
    query: str
    category: str | None
    max_price: float | None
    sort: SortOrder
    size_in_stock: str | None = None
    total: int = Field(description="Number of products shown (all matches, up to the page limit).")
    exact: bool = Field(description="False when nothing matched every search word and these are only the closest items.")
    products: list[ProductSummary]


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    products: list[ChatProduct]
    search_results: PageSearchResults | None = None
    options: list[ChatOption] = []
    saved: bool = Field(description="True when this exchange was saved to the customer's history (logged in).")


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: str
    products: list[ChatProduct]
    page_search: BrowseRequest | None = None


class ChatHistory(BaseModel):
    messages: list[HistoryMessage]


# ---------------------------------------------------------------- tool results
# Everything the lookup tools return to the agent. Values come straight from the
# catalogue and inventory tables; the agent must quote them, not estimate.

StockStatus = Literal["in_stock", "low_stock", "sold_out"]


class ProductMatch(BaseModel):
    """One search result: enough to tell similar products apart and answer simple price questions."""

    product_id: str
    name: str
    category: str
    garment_type: str
    colors: list[str]
    price: float
    total_stock: int
    sizes_in_stock: list[str]
    url: str


class ProductSearchResult(BaseModel):
    query: str
    category: str | None
    max_price: float | None
    sort: SortOrder
    size_in_stock: str | None = None
    matching_but_sold_out_in_size: list[ProductMatch] = Field(
        default_factory=list,
        description="With size_in_stock: products that match the search but are sold out in that size (up to 8).",
    )
    total_matches: int = Field(description="How many products match in total; `products` shows at most 8 of them.")
    lowest_price: float | None = Field(None, description="Lowest price among ALL matches, not just those shown.")
    highest_price: float | None = Field(None, description="Highest price among ALL matches, not just those shown.")
    all_words_matched: bool = Field(
        description="False when no product matched every search word and these are only the closest matches."
    )
    products: list[ProductMatch]


class SizeLine(BaseModel):
    size: str
    quantity: int
    status: StockStatus


class ProductInfo(BaseModel):
    """Full details for one product, including stock for every size."""

    found: bool
    product_id: str
    name: str | None = None
    category: str | None = None
    garment_type: str | None = None
    description: str | None = None
    colors: list[str] = []
    price: float | None = None
    total_stock: int | None = None
    sizes: list[SizeLine] = []
    sizes_in_stock: list[str] = []
    sold_out_sizes: list[str] = []
    url: str | None = None
    message: str | None = None


class SizeStockResult(BaseModel):
    """Stock for one product in one size, plus the other sizes still available."""

    found: bool
    product_id: str
    name: str | None = None
    requested_size: str
    size: str | None = Field(None, description="The size as stocked (XS, S, M, L, XL, XXL), or None if not recognised.")
    quantity: int | None = None
    status: StockStatus | None = None
    other_sizes_in_stock: list[str] = []
    price: float | None = None
    url: str | None = None
    message: str | None = None


class Alternative(BaseModel):
    """An in-stock product that could replace the one the customer wanted."""

    product_id: str
    name: str
    category: str
    garment_type: str
    price: float
    colors: list[str]
    requested_size_quantity: int | None = Field(None, description="Stock in the requested size, if a size was asked for.")
    sizes_in_stock: list[str]
    shared: list[str] = Field(description="What it has in common with the original, e.g. 'same Grandpa design'.")
    differences: list[str] = Field(description="How it differs from the original: style, price, colours.")
    url: str


class AlternativesResult(BaseModel):
    found: bool
    product_id: str
    name: str | None = None
    requested_size: str | None = None
    requested_size_status: str | None = Field(None, description="in_stock / low_stock / sold_out for the original in that size.")
    same_product_other_sizes: list[str] = Field(default_factory=list, description="Other sizes of the original that are in stock.")
    alternatives: list[Alternative] = []
    message: str | None = None


@dataclass
class ViewedProduct:
    product_id: str
    name: str


@dataclass
class ShopDeps:
    """Per-request context passed to the agent, built by the backend for each message.

    Customer details come only from the verified login session, never from the
    chat text. Only name and email are shared, never the password or its hash.
    The page context comes from the browser and is only used as a hint about
    what "this" means; a viewed product is checked against the catalogue first.
    """

    customer_name: str | None = None
    customer_first_name: str | None = None
    customer_email: str | None = None
    page_description: str = "unknown page"
    viewed_product: ViewedProduct | None = None

    @property
    def logged_in(self) -> bool:
        return self.customer_email is not None
