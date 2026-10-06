# Campus Customs: Usability Improvements (Problem 9)

The goal is that shoppers shouldn't have to work hard to find something, or
wonder whether the chat is responding. If their first choice isn't available,
the site should help them find another option.

This document was first written as a plan before building. It has been
updated so it only describes what was built and tested in the running app on
2026-10-06. Each section says what was built, why it helps, and how it was
checked.

---

## 1. Product filters with a clear reset (frontend)

### What it does

The **Products** page has a filter panel with:

- **Category:** All, T-Shirts, Long Sleeves, Crewnecks, Hoodies, Quarter-Zips,
  Jackets & Fleece.
- **Price:** Under $50 · $50–$70 · $70–$90 · $90 and up. The bands were
  chosen around the catalogue's real prices, which run from $32 to $98.
- **Size in stock:** XS to XXL. Only products with that size actually in stock
  are shown, not products that merely come in that size.
- **Sort:** Name (A–Z), Price low to high, Price high to low.
- **Search box:** as before.

Resetting is always easy:

- **Clear all filters (n)** sits in the filter panel and shows how many
  filters are on. It's greyed out when none are.
- If a combination finds nothing, the page says "No products match these
  filters", suggests removing one, and shows a big **Clear all filters**
  button.

Other details:

- The line under the heading sums up what's applied, e.g. "19 items ·
  T-Shirts · Under $50 · size M in stock".
- Every product card now shows its **sizes in stock**, on the Products page
  and in chat results. The chosen size is highlighted in pink.
- Filters are kept in the address, e.g.
  `/products?category=T-Shirts&price=under-50&size=M`. A filtered view can be
  shared or bookmarked, and survives Back and reload.

### Why it helps

Someone who doesn't know exactly what they want usually still knows their
**budget** and **size**. "Under $50" plus "M in stock" turns 102 products into
a short list they can actually buy. The size filter removes the frustration of
opening a product only to find their size is sold out.

A visible **Clear all** means nobody gets stuck in an empty, over-filtered
view.

### How it works

`GET /api/products` now accepts `min_price`, `max_price`, `size` and `sort`,
alongside `q` and `category`, and returns `sizes_in_stock` for each product.
The size filter checks the `inventory` table for that size with quantity
above 0.

### Checked in the running app (headless Chrome)

**Counts against the database:**
- Under $50 gave 30 products, the same as the database, all priced at $50 or
  less.
- Adding M in stock gave 24, the same as the database. Every card showed M,
  highlighted.
- Adding T-Shirts gave 19, the same as the API.

**Behaviour:**
- The address kept the filters, and a reload kept the same 19.
- The summary line and "Clear all filters (3)" were correct.
- Clear all returned to all 102 with a clean address.
- Jackets & Fleece plus Under $50 gave the "No products match" state; its
  reset button returned all 102.
- Sorting high to low ran from $98 down to $32.
- On a phone (390 px) the filters fit without sideways scrolling.

---

## 2. "Finding an answer" state, helpful errors and Try again (frontend)

### What it does

**While the assistant works:**
- A pink **"Finding an answer…"** bubble with animated dots appears
  immediately.
- After 8 seconds it changes to **"Still working on it… thanks for waiting."**
- The Send button shows **"Wait…"** and is disabled, so the question isn't
  sent twice.
- After 90 seconds the browser stops waiting and offers a retry.

**If something fails**, the chat shows a red bubble with a message that
matches what happened:

| What happened | Message |
|---|---|
| Can't reach the server (offline, or the backend is down) | "I couldn't reach the shop's server. Check your internet connection." |
| Too many messages (429) | The server's "You're sending messages quickly…" message |
| Assistant not configured (503) | The server's setup message |
| Assistant error (500 or 502) | The server's message, e.g. "Sorry, I'm having trouble answering right now…" |
| Took longer than 90 seconds | "This is taking much longer than usual, so I stopped waiting." |

Under the message:
- "Your question wasn't lost. You can send it again:"
- A **Try again** button that resends the same question. The error bubble is
  replaced by the answer, and the question isn't shown twice.

### Why it helps

Answers take a few seconds. Without a visible state, shoppers wonder whether
the chat is broken and retype or leave. A specific error tells them whether to
wait, check their connection or try again. **Try again** saves retyping.

### Checked in the running app

**Slow answer:** the answer was artificially delayed by 9.5 seconds.
- "Finding an answer…" appeared right away, and Send showed "Wait…",
  disabled.
- After 8 seconds the bubble read "Still working on it…".
- It disappeared when the answer arrived.

**Server error (502), simulated in the browser:**
- The error read "Sorry, I'm having trouble answering right now…", with Try
  again.
- Try again got a real answer. There was still only one copy of the question,
  and no error left behind.

**Dropped connection, simulated in the browser:**
- The error read "I couldn't reach the shop's server…".
- Try again got a real answer.

**Real outage:** the backend was actually stopped.
- "How much is the Boola Boola T Shirt?" showed "I couldn't reach the shop's
  server…".
- The backend was restarted, then **Try again** answered "The Boola Boola T
  Shirt is $32.00."

**Bug found and fixed:** when the backend was down, the website's dev server
returned an error with no message, so at first this would have shown the
vaguer "ran into a problem". That case is now treated as "couldn't reach the
server".

---

## 3. Better handling of vague product questions (agent and backend)

### What it does

When a question could mean **several products**, the assistant searches,
asks **one short follow-up**, and offers the **real matching products as
tappable choices**. Each choice shows a photo, name, price and sizes in stock.
Tapping one sends "I mean the Morse 1 4 Zip." and the assistant answers for
that product.

How it works:

- The agent's structured output has a new `clarify_options` field: the
  candidates' `product_id`s, taken from its search results.
- **The server builds the choices from the database.** Unknown IDs are
  dropped, so a made-up product can never appear as an option.
- Once the conversation moves on, older choices are disabled.
- The prompt's "When the customer is vague" section says:
  - don't pick one product and don't answer for only one
  - ask one question
  - offer up to 5 real candidates
  - for someone just starting ("a gift for my dad"), ask about style, budget,
    size or college

### Why it helps

Guessing the wrong product gives a confident wrong answer. Shoppers often
don't know a product's exact name. With real options, they answer with one tap
instead of typing a name they'd have to look up.

### Checked

**In the running app:**
- "Do you have the Morse one in medium?" got: "Which Morse item do you mean:
  the Morse 1/4 Zip ($72.00) or the Morse Logo T-Shirt ($32.00)? Both are
  available in medium."
  - The two options were exactly the catalogue's two Morse products.
  - Each showed its real sizes: the T-shirt shows no S, which matches S = 0.
- Tapping **Morse 1 4 Zip** got "Yes—the Morse 1/4 Zip is available in
  medium, with 8 in stock. It's $72.00." The database has M = 8.
- The old options were then disabled.

**In the scripted agent test (`tests/chat_tool_eval.py`):**
- The Morse case passed.
- "Is the Saybrook one still available?" offered only Saybrook products and
  asked which.

---

## 4. A tool that finds in-stock alternatives (agent and backend)

### What it does

`find_alternatives(product_id, size?)` is a new tool in `backend/tools.py`. It
reads only the catalogue and inventory tables. When the item or size a shopper
wants is unavailable, it returns:

- **Other sizes of the same item** that are in stock.
- Up to **4 similar products that are actually in stock**, in the requested
  size if one was given.
  - They are ranked by shared design theme from the product name (e.g.
    "grandpa", "morse", "football"), then the same category and garment
    type, then shared colours, then a close price.
- For each alternative, what is **shared** (e.g. "same theme: grandpa") and
  exactly how it **differs**, all computed from database fields:
  - style, e.g. "pullover hoodie instead of crewneck sweatshirt"
  - price, e.g. "$10.00 more ($68.00 vs $58.00)"
  - colours
  - "different design" plus the product's description, when there's no
    shared theme

The prompt tells the agent to:
- say clearly that the item is sold out
- call `find_alternatives`
- offer 2–3 of the best and say how each differs
- **only offer what the tool returned**, and never invent options

The alternatives appear as product cards under the reply.

### Why it helps

"Sold out" is a dead end. A close in-stock alternative keeps the shopper
moving, such as the same Grandpa design as a hoodie with 25 in medium. Saying
how it differs avoids surprises such as "I didn't realise it was $10 more" or
"I wanted a crewneck".

### Checked

**In the running app, on the Yale Grandpa Crewneck page (M = 0):** "Is this
available in medium?" got:
- "Medium is sold out… available in XS, S, L and XL."
- "For a medium, the Yale Grandpa Hoodie is in stock (25 available), but
  it's $68.00 and has a hoodie style."
- "The Super Heavyweight Crewneck Arched Yale Crest is $58.00 with 5 in M,
  but has a different design."

Both cards were checked against the database: M = 25 and M = 5.

**In the scripted agent test, which records the actual tool calls:**
- **Grandpa Crewneck in medium:**
  - The agent called `find_alternatives` and offered the Grandpa Hoodie with
    the price and style difference.
  - Every offered product has M in stock.
  - Every offered product was among those the tool returned.
- **Brooks Brothers bomber jacket in medium (M = 0):**
  - It offered the Brooks Brothers Double Knit Full Zip Hoodie ("same Brooks
    Brothers theme… a hoodie instead of a bomber", $88.00, 8 in M) and two
    fleeces.
  - All are in stock in M, and all came from the tool.
- **Football Left Chest T Shirt in M or XS (both 0):**
  - It offered the Tri Blend Sports Football T Shirt ("same football theme…
    heather gray or navy blue instead of navy/white"), the Boola Boola tee
    and the 2025 Yale vs Harvard tee.
  - All are in stock in M and XS according to the database.

**Bug found and fixed while building:** the first version picked alternatives
using words from product tags, such as "gray", "navy" and "ivy league". It
missed the obvious Grandpa Hoodie and treated "navy" and "navy blue" as
different colours. Themes now come from product names only, and colour names
are normalised.

---

## Overall results

- **Problem 9 browser test:** 32 of 32 checks passed in the running app.
- **Scripted agent test:** 16 of 16, including the 4 new vague-question and
  alternatives cases.
- **Earlier tests, re-run:** site, accounts, chat, page browsing and the API
  tests all pass. One older test was updated because a sold-out question now
  correctly shows in-stock alternatives instead of the sold-out item.

## Limits

- **Fixed price bands.** They suit this catalogue, but are set by hand rather
  than calculated from the prices.
- **Time-based wait messages.** The "still working" message appears after a
  set time; the website doesn't receive live progress from the agent.
- **Theme matching uses product names.** Products with very plain names such
  as "Basic Hoodie Big Yale" mostly get alternatives by category, colour and
  price.
- **The agent decides when to use these features.** Whether to ask a
  follow-up or call `find_alternatives` is up to the model. The tested
  phrasings behaved correctly, but wording can vary between runs.
