"""Read-only access to the product catalogue and inventory.

Shared by the website routes (main.py) and the assistant's tools (tools.py), so
both always show the same names, prices and stock. Only the `catalogue` and
`inventory` tables are queried, always through a read-only connection.
"""

import json
import re
import sqlite3

from db import connect_ro  # noqa: F401  (re-exported: tools use catalog.connect_ro)

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
LOW_STOCK = 3  # 1-3 units left counts as "low"

# garment_type in the database has 22 spellings for a handful of real types.
# Checked in order, so "quarter-zip" wins over "pullover" and hooded full-zips
# count as hoodies rather than jackets.
CATEGORY_RULES = [
    ("quarter-zip", "Quarter-Zips"),
    ("hood", "Hoodies"),
    ("jacket", "Jackets & Fleece"),
    ("t-shirt", "T-Shirts"),
    ("performance", "Long Sleeves"),
    ("crewneck", "Crewnecks"),
    ("mockneck", "Crewnecks"),
]
CATEGORIES = ["T-Shirts", "Long Sleeves", "Crewnecks", "Hoodies", "Quarter-Zips", "Jackets & Fleece"]

PRODUCT_SELECT = """
    SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock,
           GROUP_CONCAT(CASE WHEN i.quantity > 0 THEN i.size END) AS sizes_csv
    FROM catalogue c LEFT JOIN inventory i ON i.product_id = c.product_id
"""


def sort_sizes(sizes) -> list[str]:
    return sorted(sizes, key=lambda s: SIZE_ORDER.index(s) if s in SIZE_ORDER else len(SIZE_ORDER))


def category_for(garment_type: str) -> str:
    g = garment_type.lower()
    for needle, category in CATEGORY_RULES:
        if needle in g:
            return category
    return "Other"


def first_sentence(text: str) -> str:
    end = text.find(". ")
    return text if end == -1 else text[: end + 1]


def image_url(image_file_path: str) -> str:
    # Stored as "products/<file>.jpg", relative to data/.
    return f"/media/{image_file_path}"


def product_url(product_id: str) -> str:
    return f"/products/{product_id}"


def stock_status(quantity: int) -> str:
    if quantity <= 0:
        return "sold_out"
    if quantity <= LOW_STOCK:
        return "low_stock"
    return "in_stock"


def summary_from_row(row: sqlite3.Row) -> dict:
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "category": category_for(row["garment_type"]),
        "short_description": first_sentence(row["description"]),
        "colors": json.loads(row["colors"]),
        "price": row["price"],
        "image_url": image_url(row["image_file_path"]),
        "total_stock": row["total_stock"],
        "sizes_in_stock": sort_sizes((row["sizes_csv"] or "").split(",")) if row["sizes_csv"] else [],
    }


def all_products(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(PRODUCT_SELECT + " GROUP BY c.product_id ORDER BY c.name").fetchall()


def get_product_row(conn: sqlite3.Connection, product_id: str) -> sqlite3.Row | None:
    return conn.execute(PRODUCT_SELECT + " WHERE c.product_id = ? GROUP BY c.product_id", (product_id,)).fetchone()


def size_stock(conn: sqlite3.Connection, product_id: str) -> list[dict]:
    rows = conn.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)).fetchall()
    return sorted(
        ({"size": r["size"], "quantity": r["quantity"]} for r in rows),
        key=lambda s: SIZE_ORDER.index(s["size"]) if s["size"] in SIZE_ORDER else len(SIZE_ORDER),
    )


# ---------------------------------------------------------------- sizes

_SIZE_WORDS = {
    "xs": "XS", "x-small": "XS", "xsmall": "XS", "extra small": "XS", "extra-small": "XS",
    "s": "S", "small": "S", "sm": "S",
    "m": "M", "medium": "M", "med": "M",
    "l": "L", "large": "L", "lg": "L",
    "xl": "XL", "x-large": "XL", "xlarge": "XL", "extra large": "XL", "extra-large": "XL",
    "xxl": "XXL", "2xl": "XXL", "xx-large": "XXL", "xxlarge": "XXL", "2x": "XXL",
    "extra extra large": "XXL", "double xl": "XXL",
}


def normalize_size(size: str) -> str | None:
    """'medium' -> 'M', '2XL' -> 'XXL'. None if it isn't one of the sizes we stock."""
    return _SIZE_WORDS.get(re.sub(r"\s+", " ", size.strip().lower()))


# ---------------------------------------------------------------- search

_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "in", "of", "to", "my", "me", "i", "do", "you", "have",
    "any", "some", "is", "are", "it", "that", "this", "something", "show", "find", "looking", "want",
    "yale", "shirt", "shirts",  # nearly every product says Yale; "shirt" is too broad on its own
}
_SYNONYMS = {
    "tee": "t-shirt", "tees": "t-shirt", "tshirt": "t-shirt", "t": "t-shirt",
    "sweatshirt": "crewneck", "crew": "crewneck", "quarterzip": "quarter-zip", "1/4": "quarter-zip",
    "zip": "zip", "hoody": "hoodie", "hoodies": "hoodie", "grey": "gray", "fleeces": "fleece",
}


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9/+-]+", text.lower())
    out = []
    for w in words:
        w = _SYNONYMS.get(w, w)
        if w in _STOPWORDS or len(w) < 2 and not w.isdigit():
            continue
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]  # crude plural: hoodies -> hoodie, crewnecks -> crewneck
        out.append(w)
    return out


def search(
    conn: sqlite3.Connection,
    query: str,
    category: str | None = None,
    max_price: float | None = None,
    sort: str = "relevance",
    size: str | None = None,
) -> tuple[list[sqlite3.Row], bool]:
    """Return (all matching rows, best first; all_words_matched).

    sort: "relevance" (default), "price_low_to_high" or "price_high_to_low".
    size: only products with this size in stock ("M", "medium", "2XL"...).

    A product matches when every search word appears in its name, garment
    type, colours, tags or description. If nothing matches every word, the
    products matching the most words are returned and all_words_matched is
    False, so the caller can say the match is only partial.
    """
    words = _tokens(query)
    wanted_size = normalize_size(size) if size else None
    scored = []
    for row in all_products(conn):
        if category and category_for(row["garment_type"]) != category:
            continue
        if max_price is not None and row["price"] > max_price:
            continue
        if size is not None and wanted_size not in (row["sizes_csv"] or "").split(","):
            continue
        name = row["name"].lower()
        fields = " ".join(
            [name, row["garment_type"].lower(), row["colors"].lower(), row["search_tags"].lower(), row["description"].lower()]
        )
        hits = sum(1 for w in words if w in fields)
        name_hits = sum(1 for w in words if w in name)
        scored.append((hits, name_hits, row))

    if not words:  # category / price filter only
        rows, exact = [r for _, _, r in scored], True
    elif full := [(h, n, r) for h, n, r in scored if h == len(words)]:
        full.sort(key=lambda t: (-t[1], t[2]["name"]))
        rows, exact = [r for _, _, r in full], True
    else:
        partial = [(h, n, r) for h, n, r in scored if h > 0]
        partial.sort(key=lambda t: (-t[0], -t[1], t[2]["name"]))
        rows, exact = [r for _, _, r in partial], False
    if sort in ("price_low_to_high", "price_high_to_low"):
        rows = sorted(rows, key=lambda r: (r["price"], r["name"]), reverse=sort == "price_high_to_low")
    return rows, exact

