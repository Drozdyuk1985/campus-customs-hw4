"""Ask the real shopping assistant product questions and compare its answers with the database.

Run from the hw4 folder (needs PORTKEY_API_KEY; makes real model calls):
    .venv/bin/python tests/chat_tool_eval.py

Expected values are read live from data/campus_customs.db, not hard-coded, and
every result (question, tools called, reply, checks) is saved to
output/chat_tool_tests.json.
"""

import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HW4 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW4 / "backend"))

import agent  # noqa: E402
import catalog  # noqa: E402
from models import ShopDeps  # noqa: E402
from pydantic_ai import UsageLimits  # noqa: E402
from pydantic_ai.messages import ModelResponse, ToolCallPart  # noqa: E402


def db_product(pid: str) -> dict:
    with catalog.connect_ro() as conn:
        row = catalog.get_product_row(conn, pid)
        stock = {s["size"]: s["quantity"] for s in catalog.size_stock(conn, pid)}
    return {"name": row["name"], "price": row["price"], "stock": stock, "description": row["description"]}


def money(x: float) -> str:
    return f"${x:,.2f}"


def says_price(text: str, price: float) -> bool:
    return money(price) in text or f"${price:g}" in text and not re.search(re.escape(f"${price:g}") + r"\.\d[1-9]", text)


def mentions(text: str, *words: str) -> bool:
    t = text.lower()
    return all(w.lower() in t for w in words)


SOLD_OUT = re.compile(
    r"sold out|out of stock|none left|no .{0,20}left|0 left|not (currently )?in stock|unavailable"
    r"|neither\b.{0,40}\b(in stock|available)", re.I)
NEGATION = re.compile(r"\b(not|no|neither|nor|sold out|out of stock|unavailable)\b|n['’]t\b", re.I)


def claims_in_stock(text: str, sizes: list[str]) -> bool:
    """True if some sentence says one of these sizes is in stock/available without any negation."""
    for sentence in re.split(r"(?<=[.!?])\s+|\n", text):
        if any(size_mentioned(sentence, s) for s in sizes) and re.search(r"in stock|available", sentence, re.I):
            if not NEGATION.search(sentence):
                return True
    return False


def size_mentioned(text: str, size: str) -> bool:
    return re.search(rf"(?<![A-Za-z]){size}(?![A-Za-z])", text) is not None


async def ask(turns: list[str], deps: ShopDeps | None = None) -> dict:
    a = agent.get_agent()
    history, tools_called, out = [], [], None
    for msg in turns:
        result = await a.run(
            msg, deps=deps or ShopDeps(), message_history=history,
            usage_limits=UsageLimits(request_limit=agent.MAX_MODEL_REQUESTS, tool_calls_limit=agent.MAX_TOOL_CALLS,
                                     total_tokens_limit=agent.MAX_TOTAL_TOKENS),
        )
        for m in result.new_messages():
            if isinstance(m, ModelResponse):
                for p in m.parts:
                    if isinstance(p, ToolCallPart):
                        tools_called.append({"tool": p.tool_name, "args": p.args_as_dict()})
        history = result.all_messages()
        out = result.output
    return {"reply": out.reply, "product_ids": out.product_ids, "clarify_options": out.clarify_options,
            "tools_called": tools_called}


def alternatives_returned(r: dict) -> set[str]:
    """product_ids the find_alternatives tool could have returned for the calls the agent made."""
    import tools
    ids = set()
    for t in r["tools_called"]:
        if t["tool"] == "find_alternatives":
            res = tools.find_alternatives(**t["args"])
            ids |= {a.product_id for a in res.alternatives} | {res.product_id}
    return ids


def has_size(pid: str, size: str) -> bool:
    return db_product(pid)["stock"].get(size, 0) > 0


def build_cases() -> list[dict]:
    hoodie = db_product("basic-hoodie-big-yale")
    gcrew, ghood = db_product("yale-grandpa-crewneck"), db_product("yale-grandpa-hoodie")
    say = db_product("saybrook-college-crewneck")
    bomber = db_product("brooks-brothers-bomber-jacket-yale")
    football = db_product("football-left-chest-t-shirt")
    morse = db_product("morse-1-4-zip")
    with catalog.connect_ro() as conn:
        hoodies = [r for r in catalog.all_products(conn) if catalog.category_for(r["garment_type"]) == "Hoodies"]
    min_hoodie = min(r["price"] for r in hoodies)
    cheapest_hoodie_names = [r["name"] for r in hoodies if r["price"] == min_hoodie]
    say_out = [s for s, q in say["stock"].items() if q == 0]
    gcrew_in = [s for s, q in gcrew["stock"].items() if q > 0]

    return [
        {
            "id": "vague: two Morse products",
            "turns": ["Do you have the Morse one in medium?"],
            "expected": "Ambiguous: Morse 1 4 Zip and Morse Logo T Shirt; ask which, offer both as options",
            "checks": lambda r: {
                "asks a follow-up": "?" in r["reply"],
                "offers both Morse products as options": {"morse-1-4-zip", "morse-logo-t-shirt"} <= set(r["clarify_options"]),
                "options are all real Morse products": all("morse" in o for o in r["clarify_options"]),
            },
        },
        {
            "id": "vague: Saybrook",
            "turns": ["Is the Saybrook one still available?"],
            "expected": "3 Saybrook products (crewneck, logo tee, fleece); ask which",
            "checks": lambda r: {
                "asks a follow-up": "?" in r["reply"],
                "offers the Saybrook products": len([o for o in r["clarify_options"] if "saybrook" in o]) >= 2,
                "no non-Saybrook options": all("saybrook" in o for o in r["clarify_options"]),
            },
        },
        {
            "id": "alternatives: sold-out size",
            "turns": ["Do you have the Yale Grandpa Crewneck in medium?"],
            "expected": f"M sold out (0). Grandpa Hoodie has M={ghood['stock']['M']}; tool should be used",
            "checks": lambda r: {
                "says sold out": bool(SOLD_OUT.search(r["reply"])),
                "called find_alternatives": any(t["tool"] == "find_alternatives" for t in r["tools_called"]),
                "offers the Grandpa Hoodie": "yale-grandpa-hoodie" in r["product_ids"] and "hoodie" in r["reply"].lower(),
                "explains a difference (price or style)": re.search(
                    r"\$10|more|less|instead|style|rather than|pullover hoodie|different .{0,25}design|costs \$68", r["reply"], re.I) is not None,
                "every offered product is in stock in M": all(has_size(p, "M") for p in r["product_ids"] if p != "yale-grandpa-crewneck"),
                "only offers products the tool returned": set(r["product_ids"]) <= alternatives_returned(r) | {"yale-grandpa-crewneck"},
            },
        },
        {
            "id": "alternatives: bomber in medium",
            "turns": ["I want the Brooks Brothers bomber jacket in a medium."],
            "expected": f"M sold out (0); alternatives with M in stock, e.g. Brooks Brothers Double Knit Full Zip Hoodie (M={db_product('brooks-brothers-double-knit-full-zip-hoodie-yale')['stock']['M']})",
            "checks": lambda r: {
                "says sold out": bool(SOLD_OUT.search(r["reply"])),
                "called find_alternatives": any(t["tool"] == "find_alternatives" for t in r["tools_called"]),
                "offers at least one alternative": len([p for p in r["product_ids"] if p != "brooks-brothers-bomber-jacket-yale"]) >= 1,
                "every offered product is in stock in M": all(has_size(p, "M") for p in r["product_ids"] if p != "brooks-brothers-bomber-jacket-yale"),
                "only offers products the tool returned": set(r["product_ids"]) <= alternatives_returned(r) | {"brooks-brothers-bomber-jacket-yale"},
            },
        },
        {
            "id": "price",
            "turns": ["How much is the Basic Hoodie Big Yale?"],
            "expected": f"{hoodie['name']} costs {money(hoodie['price'])}",
            "checks": lambda r: {
                "used search/details tool": any(t["tool"] in ("search_products", "get_product_details") for t in r["tools_called"]),
                f"says {money(hoodie['price'])}": says_price(r["reply"], hoodie["price"]),
                "product card": r["product_ids"][:1] == ["basic-hoodie-big-yale"],
            },
        },
        {
            "id": "sold-out size",
            "turns": ["Do you have the Yale Grandpa Crewneck in medium?"],
            "expected": f"M is sold out (0); in stock: {', '.join(gcrew_in)}",
            "checks": lambda r: {
                "used check_size_stock or details": any(t["tool"] in ("check_size_stock", "get_product_details") for t in r["tools_called"]),
                "says M is sold out": bool(SOLD_OUT.search(r["reply"])),
                "offers in-stock sizes": sum(size_mentioned(r["reply"], s) for s in gcrew_in) >= 2,
            },
        },
        {
            "id": "stock by size",
            "turns": ["What sizes of the Saybrook College Crewneck are in stock, and how many of each?"],
            "expected": "; ".join(f"{s}={q}" for s, q in say["stock"].items()),
            "checks": lambda r: {
                "used details/size tool": any(t["tool"] in ("get_product_details", "check_size_stock") for t in r["tools_called"]),
                "every quantity correct": all(
                    re.search(rf"(?<![A-Za-z]){s}(?![A-Za-z])\D{{0,25}}?\b{q}\b|\b{q}\b\D{{0,25}}?(?<![A-Za-z]){s}(?![A-Za-z])", r["reply"])
                    for s, q in say["stock"].items() if q > 0
                ),
                f"says {'/'.join(say_out)} sold out": bool(SOLD_OUT.search(r["reply"])) and all(size_mentioned(r["reply"], s) for s in say_out),
            },
        },
        {
            "id": "low stock",
            "turns": ["Is the Basic Hoodie Big Yale available in XL?"],
            "expected": f"XL: {hoodie['stock']['XL']} left (low stock)",
            "checks": lambda r: {
                "used check_size_stock or details": any(t["tool"] in ("check_size_stock", "get_product_details") for t in r["tools_called"]),
                f"says {hoodie['stock']['XL']} left": re.search(rf"\b{hoodie['stock']['XL']}\b", r["reply"]) is not None,
            },
        },
        {
            "id": "ambiguous product",
            "turns": ["Do you have the grandpa one in large?"],
            "expected": (f"Ambiguous: {gcrew['name']} (L={gcrew['stock']['L']}) and {ghood['name']} (L={ghood['stock']['L']}); "
                         "should ask which one, or clearly give both, never guess one"),
            "checks": lambda r: {
                "names both grandpa products": mentions(r["reply"], "crewneck") and mentions(r["reply"], "hoodie"),
                "asks a follow-up question": "?" in r["reply"],
                "does not answer for only one product": not (len(r["product_ids"]) == 1),
            },
        },
        {
            "id": "no product named",
            "turns": ["Is it in stock in small?"],
            "expected": "Unclear which product: should ask which one, no stock claim",
            "checks": lambda r: {
                "asks which product": "?" in r["reply"] and re.search(r"which|what", r["reply"], re.I) is not None,
                "no stock tool guess": not any(t["tool"] == "check_size_stock" for t in r["tools_called"]),
            },
        },
        {
            "id": "description + price",
            "turns": ["Can you tell me about the Brooks Brothers bomber jacket? What does it look like and how much is it?"],
            "expected": f"{money(bomber['price'])}; {bomber['description'][:90]}…",
            "checks": lambda r: {
                f"says {money(bomber['price'])}": says_price(r["reply"], bomber["price"]),
                "describes it from the database": sum(w in r["reply"].lower() for w in ("navy", "bomber", "brooks brothers", "zip", "collar", "rib")) >= 2,
                "product card": "brooks-brothers-bomber-jacket-yale" in r["product_ids"],
            },
        },
        {
            "id": "not in catalogue",
            "turns": ["Do you sell a Harvard hoodie?"],
            "expected": "No Harvard hoodie in the catalogue (only the 2025 Yale vs Harvard T-shirt mentions Harvard)",
            "checks": lambda r: {
                "used search": any(t["tool"] == "search_products" for t in r["tools_called"]),
                "says no exact match": re.search(r"(don['’]t|do not|doesn['’]t|couldn['’]t|could not|can['’]t|\bno)\b", r["reply"], re.I) is not None,
                "any 'starting at'/'from' price is the real minimum": all(
                    float(m) == min_hoodie for m in re.findall(r"(?:starting at|from|as low as)\s+\$(\d+(?:\.\d\d)?)", r["reply"], re.I)),
                "no invented hoodie card": not any("harvard" in p and "hood" in p for p in r["product_ids"]),
            },
        },
        {
            "id": "two sizes sold out",
            "turns": ["I need the Football Left Chest T Shirt in M or XS. Do you have either?"],
            "expected": f"M={football['stock']['M']}, XS={football['stock']['XS']} (both sold out); in stock: "
                        + ", ".join(f"{s}={q}" for s, q in football["stock"].items() if q > 0),
            "checks": lambda r: {
                "says sold out": bool(SOLD_OUT.search(r["reply"])),
                # Only the part about the original item; alternatives offered later may well have M/XS.
                "does not claim M or XS in stock": not claims_in_stock(re.split(r"alternative|instead|you could|consider", r["reply"], flags=re.I)[0], ["M", "XS"]),
                "offers sizes that are in stock": any(size_mentioned(r["reply"], s) for s, q in football["stock"].items() if q > 0),
            },
        },
        {
            "id": "follow-up in context",
            "turns": ["I'm looking at the Morse quarter-zip.", "How many do you have in large? And in small?"],
            "expected": f"L={morse['stock']['L']} (sold out), S={morse['stock']['S']} (low)",
            "checks": lambda r: {
                "L sold out": bool(SOLD_OUT.search(r["reply"])),
                f"S: {morse['stock']['S']} left": re.search(rf"\b{morse['stock']['S']}\b", r["reply"]) is not None,
            },
        },
        {
            "id": "cheapest in category",
            "turns": ["What's the cheapest hoodie you have?"],
            "expected": f"Cheapest Hoodies-category price is {money(min_hoodie)}",
            "checks": lambda r: {
                f"says {money(min_hoodie)}": says_price(r["reply"], min_hoodie),
                "names a hoodie at that price": any(n.lower() in r["reply"].lower() for n in cheapest_hoodie_names),
                "no lower made-up price": all(float(p) >= min_hoodie for p in re.findall(r"\$(\d+(?:\.\d\d)?)", r["reply"])),
            },
        },
        {
            "id": "category + budget",
            "turns": ["What jackets or fleeces do you have under $100?"],
            "expected": "8 in Jackets & Fleece, all $98.00",
            "checks": lambda r: {
                "used search with filter": any(t["tool"] == "search_products" and (t["args"].get("category") or t["args"].get("max_price"))
                                               for t in r["tools_called"]),
                "prices are $98.00 only": set(re.findall(r"\$\d+(?:\.\d\d)?", r["reply"])) <= {"$98.00", "$98", "$100", "$100.00"},
            },
        },
    ]


async def main() -> int:
    cases = build_cases()
    results = []
    for case in cases:
        try:
            r = await ask(case["turns"])
            checks = case["checks"](r)
        except Exception as e:  # report and keep going
            r, checks = {"reply": None, "error": f"{type(e).__name__}: {e}"[:300], "tools_called": [], "product_ids": []}, {"ran": False}
        passed = all(checks.values())
        results.append({"id": case["id"], "turns": case["turns"], "expected_from_db": case["expected"], **r,
                        "checks": checks, "passed": passed})
        print(f"{'PASS' if passed else 'FAIL'}  {case['id']}: " + ", ".join(f"{k}={'ok' if v else 'NO'}" for k, v in checks.items()))
    out = HW4 / "output" / "chat_tool_tests.json"
    out.write_text(json.dumps({
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": agent.MODEL_NAME,
        "passed": sum(r["passed"] for r in results),
        "total": len(results),
        "results": results,
    }, indent=2, ensure_ascii=False))
    print(f"\n{sum(r['passed'] for r in results)}/{len(results)} passed -> {out.relative_to(HW4)}")
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
