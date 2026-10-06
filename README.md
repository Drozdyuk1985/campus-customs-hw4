# Campus Customs: HW4 shop website with an AI shopping assistant

A Yale apparel shop for Campus Customs (Yale SOM MGT 409, HW4).

- **Frontend:** a **React + Vite + TypeScript** website. It has product
  browsing and filters, product pages, accounts, and a chat panel.
- **Backend:** a **FastAPI** server.
- **Assistant:** a **PydanticAI** shopping assistant that looks up real
  products, prices and stock from the shop's SQLite database. It runs on
  OpenAI `gpt-5.6-luna` through the Portkey gateway.

## Where to look first

| File | What's in it |
|---|---|
| `output/app_check.html` | Screenshots of the running app (open the file in a browser) |
| `output/harness.md` | Full system reference: database, models, tools, safety, limits, audit trail, how to run |
| `output/usability.md` | The four usability improvements and why they help |
| `output/design.md` | Design changes and why |
| `output/audit_trail.json` | Append-only log of real assistant activity |
| `AI_prompts.md` | The prompts used for each problem |

## What you need

- Python **3.11+** (tested on 3.13)
- Node.js **20+** (tested on 24)
- A **Portkey API key** for the course's OpenAI access
- The course's **supplied data**: `campus_customs.db` and the `products/`
  image folder. They are **not in this repository**.

## 1. Install

From the `hw4` folder (the root of this repository):

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cd frontend
npm install
cd ..
```

## 2. Add your API key (stays on your computer)

Copy the example file and put your key in it:

```bash
cp .env.example .env
# then edit .env and replace the placeholder:
# PORTKEY_API_KEY=your-portkey-key-here
```

Notes:
- **Other ways to set it:** you can export `PORTKEY_API_KEY` in your shell
  instead, or put it in the course folder's `.env` one level up. The backend
  reads all three.
- **Keep it private:** `.env` is listed in `.gitignore`, so it can't be
  committed. The key is only used by the backend and is never sent to the
  browser.
- **Optional settings** (see `.env.example`): `PORTKEY_BASE_URL`,
  `CAMPUS_CUSTOMS_MODEL` (default `gpt-5.6-luna`), and `COOKIE_SECURE=1` when
  served over HTTPS.

If the key is missing, the site still runs. The chat replies with what to add.

## 3. Add the supplied database and product images

Put the course files here. The whole `data/` folder is ignored by git.

```
hw4/
└── data/
    ├── campus_customs.db        ← the supplied SQLite database
    └── products/                ← the supplied product photos (102 .jpg files)
        ├── basic-hoodie-big-yale.jpg
        └── ...
```

Optional, recommended: make consistent white-background display copies of the
photos. This takes about 25 seconds and writes `data/products_web/`. The
originals are never changed.

```bash
cd backend
python prepare_images.py
cd ..
```

Without this step, the site uses the original photos, some of which have black
backgrounds.

Notes on the database:
- On first start the backend adds a `sessions` table, used for logins.
- New accounts and logged-in chat history are saved in `campus_customs.db`.
- Keep a copy of the original database if you want to reset later.

## 4. Start the app (two terminals)

**Backend** (FastAPI + assistant), http://127.0.0.1:8000:

```bash
cd backend
source ../.venv/bin/activate
uvicorn main:app --reload --port 8000
```

**Frontend** (website), http://localhost:5174:

```bash
cd frontend
npm run dev
```

Open **http://localhost:5174**. The website forwards `/api` and `/media`
requests to the backend on port 8000. To use another port, set
`BACKEND_URL=http://127.0.0.1:<port>` before `npm run dev`.

To check the backend on its own, open `http://127.0.0.1:8000/api/health`. It
reports the product count, the model, and whether the key is set; it never
shows the key itself.

Test account (supplied with the assignment): `test@campuscustoms.yale.edu` /
`password`. You can also create your own account on the site.

## Features

- **Website:**
  - Home, Products, product pages, About Us, Log in and Create account
  - Product filters: category, price, size in stock, search and sort, with
    Clear all
  - Navy-and-white Yale design that works on phones and computers
- **Accounts:** sign-up, login and logout, with PBKDF2-hashed passwords and an
  HttpOnly session cookie.
- **Shopping assistant (chat panel):**
  - real prices, descriptions and stock per size from the database
  - honest "sold out" answers, plus in-stock alternatives and how they differ
  - short follow-up questions with tappable options when a question is vague
  - product cards placed on the page for "what hoodies do you have?"
  - knows which product is open ("do you have this in pink?")
  - saved history for logged-in customers
  - a "finding an answer" indicator, clear error messages, and Try again
- **Safety:**
  - Each customer can only reach their own history; this is enforced in the
    backend.
  - A check on every reply blocks secrets and other people's emails.
  - The assistant has limits on calls, tokens and time.
  - An append-only, privacy-scrubbed audit trail.

## Tests

```bash
.venv/bin/python tests/chat_tool_eval.py   # asks the real assistant 16 product questions and checks the answers against the database
cd frontend && npm run build               # type-check and production build
```

Results of the browser tests that were run are recorded in
`output/harness.md` and the `output/*_tests.json` files.

## Project layout

```
backend/    main.py (API) · agent.py (model, agent, limits) · tools.py · models.py · prompts/prompt.md
            auth.py · chat_store.py · catalog.py · audit.py · db.py · prepare_images.py
frontend/   React + Vite + TypeScript app (src/pages, src/components, src/index.css)
output/     reports, screenshots (app_check_images/), audit trail, test results
tests/      chat_tool_eval.py
data/       (not in git) supplied database and images, see step 3
```

Class project for Yale SOM MGT 409. Not the official store.
