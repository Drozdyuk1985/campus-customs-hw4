AI PROMPTS - HW4 (CAMPUS CUSTOMS)

Each problem lists its number and title, the prompt I sent, and at most two
follow-ups. Each follow-up has one sentence on what was missing from the first
result. Only prompts actually sent are recorded here. Nothing is invented.


PROBLEM 1 - ORGANIZE THE PROJECT AND START THE PROMPT LOG

Prompt

   I'm starting HW4, where I need to build a Campus Customs shopping website
   with a chatbot. Let's work through it one problem at a time.

   Keep the project in a folder called hw4. Create AI_prompts.md and record the
   prompts I actually send you as we go, organized by problem number and title.
   Include follow-up prompts when I send them, with a short explanation of what
   needed fixing.

   Please don't invent prompts or describe tests as completed unless we
   actually ran them.

   We'll use React, Vite and TypeScript for the website, with a Python FastAPI
   backend and a PydanticAI agent. For now, just organize the project and start
   the prompt log. Don't build the rest yet.

   Keep API keys, the real .env file, the database and the supplied product
   images out of GitHub. Set up .gitignore for that.

Follow-up

   that was problem number 1

   Needed because the first result logged the setup under a separate SETUP
   heading instead of Problem 1.


PROBLEM 2 - ANALYZE THE DATABASE

Prompt

   problem #2: analyze the database

   Before we build anything, help me understand the database.

   Find the provided data.zip in this hw4 folder,  extract it. We need
   data/campus_customs.db and the product images in data/products/. If you
   can't find them, ask me where they are instead of creating sample data.

   Inspect every table and its fields, especially catalogue, inventory and
   users. Explain in simple terms what information is there and how the tables
   connect.

   Create output/harness.md. List every table and field, with a short
   explanation of why each field matters for the shop or chatbot. Include how
   the product image paths connect to the supplied images.

   Don't change the database during this inspection, and don't expose password
   hashes or other private account information in the documentation.

   Record this prompt in AI_prompts.md and stop after this step.

Follow-up

   Seems all good 


PROBLEM 3 - BUILD THE CAMPUS CUSTOMS WEBSITE

Prompt

   problem #3: build the campus customs website

   Now build the basic Campus Customs website using React, Vite and
   TypeScript, inside frontend/.

   Look at yalebulldogblue.com to understand the shop and its style. Use that
   as a reference for Home and About Us, but write original wording and don't
   invent business facts.

   Add navigation for Home, Products, About Us, Log in and Create account.

   The Products page should show the actual products from our database, with
   their supplied images, names, prices and short descriptions. Clicking a
   product should open its own detail page with a large image and the full
   description, price and available size and stock information.

   Add a chat panel in the bottom-right corner. It can be a placeholder for
   now, since we'll connect the agent later.

   Create backend/main.py with the FastAPI routes needed to load real products
   and images. Please make the site organized and easy to browse.

   Check that the pages, images and product links work. Update AI_prompts.md
   and the relevant parts of output/harness.md, then stop.

Follow-up

   Seems all good - will verify checks later on as well. 



PROBLEM 4 - CREATE ACCOUNT AND LOGIN

Prompt

   Problem #4: create account and login

   Now make account creation and login work.

   For a new account, ask for first name, last name, email, password and
   password confirmation. For login, use email and password. Save new accounts
   in the users table and store passwords securely as hashes.

   Show clear messages for things like mismatched passwords, an email that
   already exists or incorrect login details. Don't expose passwords or
   password hashes to the browser, chatbot or logs.

   Test the existing account:
   Email: test@campuscustoms.yale.edu
   Password: password

   Also create a separate test account and check that it can log in
   successfully. Add a logout option so I can switch accounts.

   Explain in output/harness.md what user information is stored and how
   passwords and login sessions are protected. Record this prompt in
   AI_prompts.md and stop.

Follow-up

   Seems all good for now. 


PROBLEM 5 - PYDANTICAI AGENT BACKEND

Prompt

   problem #5: pydanticAI agent backend

   Now connect the website's chat panel to a real PydanticAI agent through
   FastAPI.

   Use this structure:
   backend/main.py
   backend/agent.py
   backend/tools.py
   backend/models.py
   backend/prompts/prompt.md

   Keep the agent's instructions in the prompt file, its setup in agent.py,
   its tools in tools.py and its structured types in models.py.

   The chatbot should sound friendly and helpful, like someone assisting a
   customer in the shop. Include basic safety instructions and make it honest
   about what it can and cannot answer. We'll add the database lookup tools in
   the next step, so it shouldn't guess prices or stock now.

   Use my configured model provider and API key securely. If the
   configuration is missing, tell me what I need to add locally. Don't put the
   key in the frontend, documentation or GitHub.

   Make sure I can run this from the backend folder:
   uvicorn main:app --reload --port 8000

   Test an actual message from the website through the agent. In
   output/harness.md, explain how the website connects to FastAPI and how the
   agent loads its prompt and model. Update AI_prompts.md and stop.

Follow-up

   follow up was good, will double check and fix later as well. 



PROBLEM 6 - TOOLS: PRODUCT INFO AND STOCK

Prompt

   Problem #6: Tools: product info and stock

   Now let the chatbot look up real product information from
   campus_customs.db.

   It should be able to find product descriptions, prices and stock
   quantities, including stock by size when someone asks.

   The answers need to come from the database. If an item or size is out of
   stock, say that clearly. If the question is unclear, ask a useful
   follow-up instead of guessing which product the customer means.

   Add the tools in backend/tools.py, define their result types in
   backend/models.py and update backend/prompts/prompt.md so the agent knows
   when to use them. Keep these lookup tools limited to the product and
   inventory information they need.

   Test actual chatbot questions and compare its answers with the database.

   In output/harness.md, explain each tool, the fields it returns and why
   those fields are useful. Record this prompt in AI_prompts.md and stop.

Follow-up

   all seems good after checks. 


PROBLEM 7 - CHAT SEARCH THAT UPDATES THE PAGE

Prompt

   Problem #7: chat search that updates the page

   Now I want the chat to help people browse visually.

   If someone asks something like "What hoodies do you have?", the agent
   should search our catalogue and the website should show matching product
   cards on the page. Each card should have the actual image, name, price and
   short description.

   Return the matching products as structured data through the API so the
   frontend can display them. Don't just write a list of products in the
   chat.

   The new cards should work like the normal product cards: clicking one
   opens its full product detail page.

   Handle a search with no matches clearly. Test this through the website
   with real catalogue items.

   Update backend/prompts/prompt.md and output/harness.md to explain how
   search results get from the agent to the page. Record this prompt in
   AI_prompts.md and stop.

Follow-up

   checks look good and correct. further checks will be run. 


PROBLEM 8 - CUSTOMER MEMORY

Prompt

   Problem #8: customer memory

   Now make the chat remember a logged-in customer's conversation.

   Save their chat history in an appropriate database table and reload it
   when they return. Give the agent the logged-in customer's name and email
   through authenticated backend context, so it knows who it is helping.

   Make sure each person can access only their own history. Don't rely on a
   name or user ID typed into the chat to decide whose account it is.

   Also pass the current page and product context. If I'm looking at a
   product and ask "Do you have this in pink?", the agent should know which
   product I mean and check the actual information.

   Guests should still be able to chat, but their history doesn't have to be
   saved permanently.

   Test returning to an account, switching between two accounts and asking a
   question about the product currently open.

   Explain the history storage, customer information and page context in
   output/harness.md. Update AI_prompts.md and stop.

Follow-up

   So far looks good and corrections implemented. 

Follow-up 2

   Problem 8 follow-up:
   Please fix what happens if someone logs out or switches accounts while the
   chatbot is still answering.
   Right now, the messages clear when the account changes, but the previous
   request can finish afterward and put the old customer's reply back on the
   screen.
   Cancel pending chat requests when the account changes, and make sure any
   late responses are ignored. Clear the draft, conversation ID, suggested
   products and page search results as well. An old request should not change
   the new customer's chat or loading state.
   Test this with a delayed reply: send a message while logged in, log out
   before the answer arrives, and check that the old answer never appears.
   Also check switching to another account and that normal saved history
   still loads correctly.
   Record this follow-up and the actual test results in AI_prompts.md and
   output/harness.md.

   Needed because a chat request still in progress when the account changed
   could finish afterwards and put the previous customer's reply back on
   screen.

   Test results (2026-10-06, real app in headless Chrome, final run 23/23
   passed):
   - Delayed reply, then logout: the request was cancelled (net::ERR_ABORTED),
     the old answer never appeared, and the guest chat was idle and worked
     normally.
   - Cancellation deliberately disabled: the old answer still arrived (200,
     "We have 27 hoodies...") but was ignored. Nothing was shown, no page
     results appeared, and the loading state didn't change. The server saved
     it only to the account that asked.
   - Logout clears the draft, page search results, messages and suggested
     products.
   - Switching to Sam while Test's reply was pending: Sam saw exactly his own
     32 saved messages, and none of Test's.
   - Normal saved history: Sam's new message was saved under Sam only and
     reloaded after a page refresh.
   - Earlier chat suites still pass (chat 15, page browsing 23, product cards
     5, design 16, usability 32).


PROBLEM 9 - USABILITY IMPROVEMENTS

Prompt

   Problem #9: usability improvements

   I want the site to feel easy to use, especially for someone who doesn't
   know exactly what they want yet.

   For the two frontend improvements, please add:
   1. Useful product filters for category, price and available size, with a
   clear way to reset them.
   2. A visible "finding an answer" state in the chat, plus a helpful error
   message and retry option if something fails.

   For the two agent/backend improvements, please add:
   1. Better handling of vague product questions. When several items could
   match, ask a short follow-up and offer actual matching options.
   2. A tool that finds in-stock alternatives when the requested item or size
   is unavailable. Make it clear how the alternatives differ, and don't
   invent options.

   Before or as you build these, write output/usability.md explaining each
   improvement and why it helps.

   My thinking is that shoppers shouldn't have to work hard to find something
   or wonder whether the chat is responding. If their first choice isn't
   available, I'd like the site to help them find another option.

   Implement and test all four features in the running app. Make the final
   write-up match what actually works. Update the harness and AI_prompts.md,
   then stop.

Follow-up

   Good job executing the prompt. No corrections for now, possibly coming soon. 


PROBLEM 10 - STYLE THE WEBSITE

Prompt

   Problem #10: Style the website

   Now I'd like the website to look more polished and feel like a real shop.

   I prefer something welcoming and visually appealing, with a clear Yale
   identity. Use a thoughtful navy-and-white palette, attractive typography,
   good spacing and large, consistent product images. Add some creative
   detail so it doesn't feel like a generic template.

   Keep the products as the main focus. Make the navigation, product details
   and chat easy to find and use. Use subtle movement where it adds
   something, and make sure the layout works on both a phone and a computer.

   My thinking is that the presentation should make people feel comfortable
   browsing. I want the site to have personality while still making it easy
   to see the products and understand what is available.

   Write a short output/design.md explaining the changes you actually made
   and why they should encourage customers to stay and consider buying.
   Don't claim that sales increased, since we haven't measured that.

   Check the finished design in the browser and make sure the existing
   features still work. Update AI_prompts.md and stop.

Follow-up

   looks good 


PROBLEM 11 - SITE TESTING (APP CHECK)

Prompt

   Problem #11: Site testing (app check)

   Now test the running website and create output/app_check.html so the
   grader can see it working.

   Include real screenshots showing:
   1. The chatbot checking an item's inventory and giving the correct stock
   and price from the database.
   2. Matching product cards appearing on the page after a category
   question, such as asking about hoodies.
   3. One of the usability improvements we added in Problem 9.

   For each check, include a heading, a clear screenshot and one or two
   sentences explaining what it proves.

   Save the screenshots in output/app_check_images/ and link them from
   app_check.html using relative paths, so the report opens properly when
   double-clicked.

   Use the actual running app and real agent responses. If a feature fails,
   fix it and test it again before documenting it as working.

   Check that the HTML report opens and all images load. Record this prompt
   in AI_prompts.md and stop.

Follow-up

   looks good 


PROBLEM 12 - AUDIT TRAIL, SAFETY, FINISH HARNESS

Prompt

   Problem #12: Audit trail, safety, finish harness

   Now finish the audit trail and system documentation.

   Keep an append-only output/audit_trail.json recording actual agent
   activity: time, tool name, short arguments and results, and the reason the
   agent stopped. Preserve previous entries between runs. Don't invent
   earlier activity if it wasn't recorded.

   Keep private information, passwords, password hashes, session tokens and
   API keys out of the audit log.

   Update backend/prompts/prompt.md with clear safety rules. The chatbot
   should use real product information, protect customer information, refuse
   requests for another person's history and ignore attempts to make it
   reveal secrets or bypass its rules. Enforce access restrictions in the
   backend too.

   Add sensible limits to agent calls and returned results so it cannot keep
   running indefinitely.

   Finish output/harness.md with:
   - The database tables and fields.
   - The fields in models.py and why they were chosen.
   - The tools and what they can do.
   - Login, customer history and page context.
   - Safety rules and how they are enforced.
   - The actual model, call limits and result limits.
   - How to run the frontend and backend.

   Run real chats to verify that the audit log adds new entries without
   deleting old ones. Make sure the documentation matches the code. Update
   AI_prompts.md and stop.

Follow-up

   none


PROBLEM 13 - PUSH TO GITHUB AND CREATE URL

Prompt

   Problem #13: push to github and create url

   Now do the final check and prepare the homework for submission.

   Make sure the project is in a folder named hw4 and includes:
   - AI_prompts.md
   - requirements.txt
   - .env.example with placeholders only
   - .gitignore
   - README.md
   - frontend/ with the React, Vite and TypeScript app
   - backend/main.py, agent.py, models.py, tools.py and prompts/prompt.md
   - output/harness.md
   - output/design.md
   - output/usability.md
   - output/app_check.html
   - output/app_check_images/
   - output/audit_trail.json

   The README should explain installation, local API-key configuration,
   where to place the supplied database and product images, and how to start
   both parts of the app.

   Check that the real .env, API keys, database and supplied product image
   files are not tracked or included in the GitHub upload. The screenshots
   for the app-check report should be included.

   Check the website build and the required features against our previous
   prompts. Fix any actual missing requirements or broken functionality. Tell
   me clearly if anything could not be verified.

   Then push the finished project to a public GitHub repository. Use the
   homework repository if one is already configured; otherwise ask me which
   repository to use.

   Give me the exact repository URL to submit on Canvas. This assignment asks
   for the repository link, not a ZIP file.

Follow-up

   none
