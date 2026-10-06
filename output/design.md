# Campus Customs: Design Notes (Problem 10)

The aim was a site that feels like a real Yale shop: welcoming, easy to browse
and clearly about the products. This note lists the changes actually made and
why they should encourage customers to stay and consider buying.

These are design reasons, not measured results. We haven't tested the design
with shoppers or tracked sales, so no claim is made that it increases sales.

## What changed and why

### 1. A navy-and-white Yale palette

- **What:** the dark black-and-pink look was replaced with **Yale Blue
  (#00356B)**, a deeper navy for headings and the footer, white for cards and
  photo frames, and a **warm ivory** page background. A lighter Yale blue
  (#286DC0) is used sparingly for links, focus rings and small accents. Stock
  colours stay meaningful: green for in stock, amber for low, grey and
  struck-through for sold out.
- **Why:** shoppers instantly recognise navy and white as Yale, so the shop
  feels like it belongs to the place they care about. The ivory background
  makes the page feel warmer than stark white, and keeps the white product
  cards standing out.

### 2. Typography with character

- **What:** headings use **Fraunces**, a soft, slightly old-style serif that
  feels collegiate. Body text uses **Inter**, which is easy to read at small
  sizes. Both fonts are bundled with the site, so nothing loads from an
  outside service.
- **Why:** the serif gives the shop personality and an "established
  campus store" feel. The clean sans-serif keeps prices, sizes and
  descriptions easy to scan.

### 3. Large, consistent product photos

- **What:** 74 of the 102 supplied photos had black backgrounds and 28 had
  white, which looked patchy.
  - A new script, `backend/prepare_images.py`, makes display copies with the
    black background turned white. It works from the image edges, plus the
    tall, narrow gaps between sleeves and body. Navy garments and black crest
    details are left alone, and I checked every image on a contact sheet.
  - The originals in `data/products/` are untouched. The backend serves the
    copies from `data/products_web/` when they exist.
  - Every photo now sits in the same white square frame, at the same size and
    padding.
- **Why:** consistent photos make the product the hero and let shoppers
  compare items side by side without being distracted by the backgrounds.

### 4. Creative details so it isn't a template

- **Crest:** a custom shield monogram ("CC"), used in the header and footer.
  It's an original mark, not a Yale logo.
- **"Varsity" rule:** a double line under section headings, borrowed from the
  double lines on the shop's own Yale wordmark shirts.
- **Stitched patches:** category tiles look like embroidered patches, with a
  dashed "stitched" border around each photo.
- **Polaroid hero:** three real products in tilted white frames, with
  handwritten-style captions, on a navy background with faint pinstripes and
  a large watermark "Y".
- **Ribbon:** a slow-moving strip of themes that really appear in the
  catalogue: residential colleges, graduate schools, varsity sports, Mom ·
  Dad · Grandpa.
- **Hero facts strip:** "102 styles · 6 categories · XS–XXL · $32–$98". It's
  calculated from the database, so it's always true.
- **Why:** these small touches give the shop a personality and a sense of
  place, while staying quiet enough not to compete with the products.

### 5. Products first, with easy navigation

- **Top bar:** a slim navy announcement bar with the two facts the real shop
  states: officially licensed Yale apparel, and the address at 57 Broadway.
- **Header:** sticky, with Home, Products and About Us, and an animated
  underline under the current page.
- **Home:**
  - categories come straight after the hero
  - then real product rows
  - then a "Three easy ways to find yours" section: filter by size and
    budget, ask the assistant, or visit the shop
- **Product cards:**
  - They lift slightly and zoom the photo on hover, with a "View details →"
    label.
  - They show the price and the sizes in stock.
- **Product page:**
  - big sticky photo
  - serif name and price
  - colour chips
  - clear size boxes with a coloured edge: green in stock, amber low, grey
    sold out
- **Footer:** organised into Shop, Help and Visit columns.
- **Why:** shoppers who aren't sure what they want can always see where they
  are, what's available and what to do next. Showing sizes in stock early
  avoids the disappointment of finding a sold-out size at the last step.

### 6. The chat is easy to find

- **Where to find it:**
  - "Ask the assistant" in the header, with a small green "available" dot.
  - A labelled **"Ask us"** button in the corner, which slides in gently once.
  - A step in "Three easy ways".
  - An **"Ask the assistant"** button in the hero.
- **On a product page:** a "Questions about this piece?" box with ready-made
  questions such as "Is this in my size?". Each opens the chat with the
  question already typed in.
- **Restyled panel:**
  - navy header
  - navy bubbles for the customer's messages, white for the assistant's
  - matching product cards and options
- **Why:** shoppers who are unsure are the ones most likely to leave. Putting
  help in front of them at the moment of doubt gives them a reason to stay.

### 7. Subtle movement, only where it helps

- Sections fade up gently as they scroll into view.
- Cards lift on hover, and the hero photos float slowly.
- The ribbon drifts, and the chat button slides in once.
- Anyone whose device asks for **reduced motion** gets a still page: no
  animations, and everything visible immediately.
- **Why:** light motion makes the page feel alive and guides the eye to new
  sections, without getting in the way.

### 8. Works on phones and computers

- **Phone (390 px):**
  - one-column hero
  - three-across category patches
  - two-across product grid (descriptions hidden to save space)
  - stacked filters
  - a round chat button
  - the header "Ask" link is hidden, because the chat button is always there
- **Laptop (1024 px) and desktop (1366 px):** the full layout. On wide
  screens the page makes room for the open chat panel instead of hiding
  results behind it.
- **Why:** many shoppers browse on their phone. They should get the same
  clear products and help, without zooming or sideways scrolling.

## How it was checked

All checks were in Chrome against the running site on 2026-10-06.

**Visual review** of screenshots at 1366 px and 390 px: Home, Products,
product page, About and Log in. Issues found and fixed during the review:
1. Section labels sat beside their headings instead of above them.
2. The footer crest's letters were invisible.
3. Black gaps between sleeves and body remained in about 30 photos.
4. Small notches on the size boxes looked like stray dots.
5. Category tiles were one per row on phones.
6. The header "Ask the assistant" link was cut off on phones.

**Design checks (16/16):**
- both fonts load
- the navy/white palette is applied
- photos are served from the white-background copies
- the header link, the Home "Ask" card and the product page's
  "Is this in my size?" each open the chat (the last two pre-fill a question)
- with reduced motion on, every section is visible and the ribbon is still
- no sideways scrolling on six pages at phone width, or at 1024 px
- the chat button is a 44 px+ tap target
- no page errors

**Existing features**, re-run on the new design, all passed:
- site and navigation: 29
- accounts: 20 (browser) and 16 (API)
- chat: 15
- product cards in chat: 5
- chat results on the page: 23
- Problem 9 usability features: 32 (filters, chat states including a real
  backend outage, options and alternatives)

The usability run first stopped partway when run straight after the other
chat suites. The server log shows the chat's own limit of 12 messages per
minute per guest had kicked in (one 429 response). Run on its own, it passed
32/32. This was a test-pacing issue, not a design change.

## Not done or not measured

- No testing with real shoppers, and no sales or conversion tracking. The
  "why" notes above are reasoning, not results.
- The display images come from an automatic background fill. They looked
  right on review, but a few low-resolution photos, such as Basic Hoodie Big
  Yale, have slightly rough edges inherited from the originals.
- Accessibility was improved (focus rings, tap sizes, reduced motion, colour
  contrast in navy on white), but not audited with a screen reader.
