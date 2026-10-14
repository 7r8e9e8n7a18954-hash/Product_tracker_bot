## Quick setup (Telegram token)

1. In Telegram, open **@BotFather**, create/select your bot, and copy its **new** token.
2. Open the `.env` file included in this project. Replace `PASTE_YOUR_NEW_TELEGRAM_TOKEN_HERE` with your token (keep it private).
3. Install dependencies: `python -m pip install -r requirements.txt`
4. Start the bot: `python -m app.main`
5. Never upload `.env` to GitHub. The `.env` file is excluded by `.gitignore`.

The download contains a placeholder, **not your actual token**. If a token was previously shared in chat, revoke it in @BotFather and use a new one.

---

# Products Detail Track Bot

A Telegram shopping-link helper built with Python, aiogram, SQLite, and optional scheduled checks.

## What it does
- Accepts supported product links from users.
- Saves product links locally per Telegram user.
- Checks public product metadata through shop-specific adapters.
- `/find PRODUCT NAME` opens search pages on Amazon India, Flipkart, and Meesho to help find possible matching listings.
- `/compare` fetches metadata for two links, compares prices when both are verified, and gives a cautious title-similarity signal.
- Saves verified price history and sends a Telegram notification when a later verified price is lower.
- `/history ID` shows recent stored price checks.
- Uses a local SQLite database; no external database is required.
- Does **not** use an AI API key.
- Does **not** invent prices, discounts, product details, or tracking history.
- Includes initial metadata adapters for Amazon India, Flipkart India, and Meesho. They read public JSON-LD/Open Graph metadata where available and do not bypass CAPTCHAs, login walls, or anti-bot restrictions.
- Price monitoring only works while the bot process and scheduler are running, and only for shops that have a working permitted adapter.

## Requirements
- Python 3.11+
- A Telegram bot token from BotFather
- Internet access for Telegram and supported product websites

## Setup
1. Create a bot with Telegram's official `@BotFather`.
2. Copy `.env.example` to `.env`.
3. Put your **newly generated** bot token in `.env` as `BOT_TOKEN=...`.
4. Install dependencies:
   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\activate
   # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```
5. Start the bot:
   ```bash
   python -m app.main
   ```

## Security note
A bot token is a password. Never commit `.env`, paste the token into chats, or share it publicly. If a token has ever been exposed, revoke it in BotFather and use a fresh one.

## Important limitations
- The adapters may fail if a shop blocks automated requests, changes page markup, or omits structured metadata. They intentionally do not bypass access restrictions.
- Use these adapters only where the shop terms and applicable law permit the intended access. Confirm that a displayed price is current before relying on it.
- `/find` creates direct search links; it does not scrape shop search results or automatically prove that listings are identical.
- Cross-shop title similarity is a rough heuristic, not a guarantee. Verify product model, size, variant, seller, delivery, and return policy.
- Price history starts only after a verified price is successfully retrieved. A first successful check sets a baseline; notifications are sent on subsequent price drops.
- Scheduled checks are sequential and run inside this process. Keep the bot online; respect each shop's terms and avoid increasing request frequency aggressively.
- The scheduler is in-process. It stops when the bot process stops.
- SQLite stores data on the machine running the bot. Back up `data/` if needed.
- This project is a starter implementation, not a hosted service.

## Project layout
```text
app/
  main.py          Telegram handlers
  adapters/        Amazon India, Flipkart, Meesho metadata adapters
  config.py        Environment configuration
  database.py      SQLite persistence
  security.py      URL validation / SSRF guard
  shops.py         Shop adapter interface
  scheduler.py     Periodic checks (supported adapters only)
tests/
  test_security.py
.env.example
requirements.txt
```

## Tests
```bash
python -m unittest discover -s tests -v
```
