"""Tools the shopping assistant can call.

The product tools only read the `catalogue` and `inventory` tables, through a
read-only connection (catalog.py). They never see users, passwords, sessions
or chat history.
"""

import re
from typing import Literal

import catalog
from models import (
    Alternative, AlternativesResult, ProductInfo, ProductMatch, ProductSearchResult, SizeLine, SizeStockResult,
)

MAX_SEARCH_RESULTS = 8

# Fixed facts only.
SHOP_INFO = {
    "shop": "Campus Customs, which runs Yale Bulldog Blue (officially licensed Yale merchandise)",
    "store_address": "57 Broadway, New Haven, CT 06511",
    "clothing_categories_on_this_site": catalog.CATEGORIES,
    "sizes_listed_on_this_site": catalog.SIZE_ORDER,
    "low_stock_means": f"{catalog.LOW_STOCK} or fewer left in that size",
    "assistant_can": [
        "search the product catalogue and give real prices, descriptions and colours",
        "check stock for every size of a product",
        "help customers choose (style, who it's for, college/school/sport, colours)",
        "explain how to browse, filter and search the website",
    ],
    "assistant_cannot": [
        "take orders or payments, hold or reserve items, or change accounts",
        "answer questions about orders, refunds, shipping or delivery times",
        "promise future restocks or discounts",
    ],
}


def get_shop_info() -> dict:
    """Fixed facts about Campus Customs and this website, and what the assistant can and cannot do."""
    return SHOP_INFO


def _sizes_in_stock(conn, product_id: str) -> list[str]:
    return [s["size"] for s in catalog.size_stock(conn, product_id) if s["quantity"] > 0]


def search_products(
    query: str,
    category: str | None = None,
    max_price: float | None = None,
    sort: Literal["relevance", "price_low_to_high", "price_high_to_low"] = "relevance",
    size_in_stock: str | None = None,
) -> ProductSearchResult:
    """Search the catalogue by words such as a product name, college, school, sport, colour or garment type.

    Use this first whenever the customer mentions a product or a kind of product,
    to find the exact product_id. Returns up to 8 matches with price, total stock
    and the sizes in stock, plus the total number of matches and the lowest and
    highest price across all of them. If several products match, ask the customer which one
    they mean instead of picking one.

    Args:
        query: Search words, e.g. "saybrook crewneck", "navy hoodie", "baseball". Use "" to list by category/price only.
        category: Optional filter; one of T-Shirts, Long Sleeves, Crewnecks, Hoodies, Quarter-Zips, Jackets & Fleece.
        max_price: Optional highest price in US dollars.
        sort: "relevance" (default), or "price_low_to_high" / "price_high_to_low" for cheapest / most expensive questions.
        size_in_stock: Optional size (XS-XXL, or "medium" etc.) for LIST questions ("which hoodies come in L").
            `products` then only has items in stock in that size; items that match but are sold out in
            that size are listed separately in `matching_but_sold_out_in_size`.
    """
    if category is not None and category not in catalog.CATEGORIES:
        category = None
    with catalog.connect_ro() as conn:
        wanted = catalog.normalize_size(size_in_stock) if size_in_stock else None  # unknown sizes are ignored
        matches, all_matched = catalog.search(conn, query, category, max_price, sort)
        # With a size filter, keep the products that match but are sold out in that size separately,
        # so a sold-out item is reported as sold out, not as "not found".
        sold_out_in_size = []
        if wanted:
            sold_out_in_size = [r for r in matches if wanted not in (r["sizes_csv"] or "").split(",")]
            matches = [r for r in matches if wanted in (r["sizes_csv"] or "").split(",")]
        rows = matches[:MAX_SEARCH_RESULTS]

        def match(r):
            return ProductMatch(
                product_id=r["product_id"],
                name=r["name"],
                category=catalog.category_for(r["garment_type"]),
                garment_type=r["garment_type"],
                colors=catalog.summary_from_row(r)["colors"],
                price=r["price"],
                total_stock=r["total_stock"],
                sizes_in_stock=_sizes_in_stock(conn, r["product_id"]),
                url=catalog.product_url(r["product_id"]),
            )

        products = [match(r) for r in rows]
        sold_out_matches = [match(r) for r in sold_out_in_size[:MAX_SEARCH_RESULTS]]
    prices = [r["price"] for r in matches]
    return ProductSearchResult(
        query=query, category=category, max_price=max_price, sort=sort,
        size_in_stock=wanted,
        matching_but_sold_out_in_size=sold_out_matches,
        total_matches=len(matches),
        lowest_price=min(prices) if prices else None,
        highest_price=max(prices) if prices else None,
        all_words_matched=all_matched, products=products,
    )


def get_product_details(product_id: str) -> ProductInfo:
    """Full details for one product: description, colours, price, and stock for every size.

    Use this when the customer asks about a specific product's description,
    price or overall availability.

    Args:
        product_id: The exact product_id from search_products, e.g. "basic-hoodie-big-yale".
    """
    with catalog.connect_ro() as conn:
        row = catalog.get_product_row(conn, product_id)
        if row is None:
            return ProductInfo(found=False, product_id=product_id,
                               message="No product with that ID. Use search_products to find the right one.")
        sizes = [SizeLine(size=s["size"], quantity=s["quantity"], status=catalog.stock_status(s["quantity"]))
                 for s in catalog.size_stock(conn, product_id)]
    summary = catalog.summary_from_row(row)
    return ProductInfo(
        found=True,
        product_id=product_id,
        name=row["name"],
        category=summary["category"],
        garment_type=row["garment_type"],
        description=row["description"],
        colors=summary["colors"],
        price=row["price"],
        total_stock=row["total_stock"],
        sizes=sizes,
        sizes_in_stock=[s.size for s in sizes if s.quantity > 0],
        sold_out_sizes=[s.size for s in sizes if s.quantity == 0],
        url=catalog.product_url(product_id),
    )


def check_size_stock(product_id: str, size: str) -> SizeStockResult:
    """How many of one product are in stock in one size, plus which other sizes are available.

    Use this when the customer asks about a particular size. Accepts XS, S, M, L,
    XL, XXL or words like "medium", "extra large", "2XL".

    Args:
        product_id: The exact product_id from search_products.
        size: The size the customer asked for.
    """
    with catalog.connect_ro() as conn:
        row = catalog.get_product_row(conn, product_id)
        if row is None:
            return SizeStockResult(found=False, product_id=product_id, requested_size=size,
                                   message="No product with that ID. Use search_products to find the right one.")
        stock = {s["size"]: s["quantity"] for s in catalog.size_stock(conn, product_id)}
    in_stock = [s for s, q in stock.items() if q > 0]
    common = dict(found=True, product_id=product_id, name=row["name"], requested_size=size,
                  price=row["price"], url=catalog.product_url(product_id))
    normalized = catalog.normalize_size(size)
    if normalized is None or normalized not in stock:
        return SizeStockResult(**common, other_sizes_in_stock=in_stock,
                               message=f"'{size}' isn't a size this product comes in. Sizes: {', '.join(stock)}.")
    quantity = stock[normalized]
    return SizeStockResult(
        **common,
        size=normalized,
        quantity=quantity,
        status=catalog.stock_status(quantity),
        other_sizes_in_stock=[s for s in in_stock if s != normalized],
    )


ALL_TOOLS = [get_shop_info, search_products, get_product_details, check_size_stock]


# ---------------------------------------------------------------- alternatives

# Words that describe the garment or the shop rather than the design/theme.
_GENERIC = {
    "yale", "t", "shirt", "tee", "tshirt", "hoodie", "hood", "hooded", "crewneck", "crew", "neck", "sweatshirt",
    "zip", "1", "4", "2", "0", "quarter", "full", "pullover", "jacket", "fleece", "sweater", "long", "sleeve",
    "left", "chest", "logo", "campus", "customs", "college", "merch", "university", "apparel", "the", "of",
    "and", "with", "s", "l", "school", "sports", "tri", "blend", "basic", "big",
}


def _theme_words(row) -> set[str]:
    """Design/theme words from the product name, e.g. 'grandpa', 'morse', 'football'.

    Only the name is used: tags and descriptions mention colours and styles
    ("navy", "ivy league") that would make unrelated products look alike.
    """
    words = set(re.findall(r"[a-z]+", row["name"].lower()))
    return {w for w in words if w not in _GENERIC and len(w) > 2}


def _norm_color(c: str) -> str:
    c = c.lower().strip().replace("grey", "gray")
    return {"navy blue": "navy"}.get(c, c)


def _money_diff(alt: float, orig: float) -> str:
    if alt == orig:
        return f"same price (${alt:.2f})"
    return f"${abs(alt - orig):.2f} {'more' if alt > orig else 'less'} (${alt:.2f} vs ${orig:.2f})"


def find_alternatives(product_id: str, size: str | None = None) -> AlternativesResult:
    """Find in-stock alternatives when a product, or a size of it, is unavailable.

    Returns the other in-stock sizes of the same product and up to 4 similar
    products that are in stock (in the requested size, if one is given). Each
    alternative lists what it shares with the original and exactly how it
    differs (style, price, colours). Only offer alternatives this tool returns.

    Args:
        product_id: The exact product_id the customer wanted (from search_products).
        size: The size they need, e.g. "M" or "medium". Omit if any size will do.
    """
    with catalog.connect_ro() as conn:
        orig = catalog.get_product_row(conn, product_id)
        if orig is None:
            return AlternativesResult(found=False, product_id=product_id,
                                      message="No product with that ID. Use search_products to find the right one.")
        wanted = catalog.normalize_size(size) if size else None
        if size and wanted is None:
            return AlternativesResult(found=True, product_id=product_id, name=orig["name"], requested_size=size,
                                      message=f"'{size}' isn't a size we stock (XS, S, M, L, XL, XXL).")
        orig_stock = {s["size"]: s["quantity"] for s in catalog.size_stock(conn, product_id)}
        stock = {r["product_id"]: {s["size"]: s["quantity"] for s in catalog.size_stock(conn, r["product_id"])}
                 for r in catalog.all_products(conn)}
        rows = catalog.all_products(conn)

    orig_cat = catalog.category_for(orig["garment_type"])
    orig_colors = catalog.summary_from_row(orig)["colors"]
    orig_theme = _theme_words(orig)
    scored = []
    for r in rows:
        if r["product_id"] == product_id:
            continue
        qty = stock[r["product_id"]].get(wanted, 0) if wanted else r["total_stock"]
        if qty <= 0:
            continue  # only things the customer could actually buy
        cat = catalog.category_for(r["garment_type"])
        colors = catalog.summary_from_row(r)["colors"]
        theme = orig_theme & _theme_words(r)
        shared_colors = [c for c in colors if _norm_color(c) in {_norm_color(o) for o in orig_colors}]
        score = (4 * len(theme) + (2 if cat == orig_cat else 0)
                 + (1 if r["garment_type"].lower() == orig["garment_type"].lower() else 0)
                 + 0.5 * len(shared_colors) - abs(r["price"] - orig["price"]) / 30)
        scored.append((score, r, cat, colors, theme, shared_colors, qty))
    scored.sort(key=lambda t: (-t[0], t[1]["name"]))

    alternatives = []
    for score, r, cat, colors, theme, shared_colors, qty in scored[:4]:
        shared = []
        if theme:
            shared.append("same theme: " + ", ".join(sorted(theme)))
        if cat == orig_cat:
            shared.append(f"same category ({cat})")
        if shared_colors:
            shared.append("shared colours: " + ", ".join(shared_colors))
        differences = []
        if r["garment_type"].lower() != orig["garment_type"].lower():
            differences.append(f"style: {r['garment_type']} instead of {orig['garment_type']}")
        differences.append("price: " + _money_diff(r["price"], orig["price"]))
        if {_norm_color(c) for c in colors} != {_norm_color(c) for c in orig_colors}:
            differences.append(f"colours: {', '.join(colors)} (original: {', '.join(orig_colors)})")
        if not theme:
            differences.append("different design: " + catalog.first_sentence(r["description"]))
        alternatives.append(Alternative(
            product_id=r["product_id"], name=r["name"], category=cat, garment_type=r["garment_type"], price=r["price"],
            colors=colors, requested_size_quantity=qty if wanted else None,
            sizes_in_stock=[s for s, q in stock[r["product_id"]].items() if q > 0],
            shared=shared, differences=differences, url=catalog.product_url(r["product_id"]),
        ))

    return AlternativesResult(
        found=True,
        product_id=product_id,
        name=orig["name"],
        requested_size=wanted,
        requested_size_status=catalog.stock_status(orig_stock.get(wanted, 0)) if wanted else None,
        same_product_other_sizes=[s for s, q in orig_stock.items() if q > 0 and s != wanted],
        alternatives=alternatives,
        message=None if alternatives else "No similar products are in stock in that size.",
    )


ALL_TOOLS.append(find_alternatives)
