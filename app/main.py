import asyncio
import html
import re
from difflib import SequenceMatcher
from urllib.parse import urlparse

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from app.config import load_settings
from app.database import Database
from app.security import validate_product_url
from app.shops import registry
from app.scheduler import build_scheduler

settings = load_settings()
db = Database(settings.database_path)
bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 My saved products", callback_data="list")],
        [InlineKeyboardButton(text="🔎 Check a product link", callback_data="help_check"),
         InlineKeyboardButton(text="⚖️ Compare links", callback_data="compare_help")],
        [InlineKeyboardButton(text="ℹ️ Features & limitations", callback_data="about")],
    ])

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🛍 <b>Products Detail Track Bot</b>\n\n"
        "Send a product link to save it and check available public product metadata.\n\n"
        "🔎 <code>/find product name</code> — open shop searches to find possible alternatives\n"
        "⚖️ /compare — compare two product links when verified prices are available\n"
        "📉 /history ID — view saved price-check history\n\n"
        "⚠️ Supported metadata adapters: Amazon India, Flipkart, and Meesho. Shops may block automated access or omit price metadata, so live prices and exact product matches are not guaranteed.\n\n"
        "Choose an option below:",
        reply_markup=main_keyboard()
    )

@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "Commands:\n/start — open menu\n/products — list saved links\n"
        "/find PRODUCT NAME — search the same query on supported shops\n"
        "/compare — send two product URLs on separate lines\n"
        "/history ID — recent saved price checks\n/delete ID — delete a saved link\n\n"
        "To save a product, send its full https:// link."
    )

@dp.message(Command("products"))
async def products_command(message: Message):
    await show_products(message)

async def show_products(message: Message):
    rows = db.list_products(message.from_user.id)
    if not rows:
        await message.answer("Your saved product list is empty. Send a product URL to add one.")
        return
    lines = ["<b>📦 Your saved product links</b>"]
    for row in rows:
        lines.append(
            f"\n<b>#{row['id']}</b> — {html.escape(row['title'])}\n"
            f"<a href=\"{html.escape(row['url'], quote=True)}\">Open product link</a>\n"
            f"Shop/domain: {html.escape(row['shop'])}"
        )
        if row["last_price"] is not None:
            lines.append(f"\nLast verified price: {row['last_price']:.2f} {html.escape(row['currency'] or '')}")
    lines.append("\n\nDelete one with <code>/delete ID</code>.")
    await message.answer("\n".join(lines), disable_web_page_preview=True)

@dp.message(Command("find"))
async def find_command(message: Message):
    query = (message.text or "").partition(" ")[2].strip()
    if not query:
        await message.answer("Use: <code>/find wireless headphones</code>")
        return
    if len(query) > 160:
        await message.answer("Please keep the search phrase under 160 characters.")
        return
    links = registry.search_links(query)
    lines = [f"<b>🔎 Search results for:</b> {html.escape(query)}", "These are shop search pages, not confirmed identical products:"]
    lines.extend(f'• <a href="{html.escape(url, quote=True)}">{html.escape(shop)} search</a>' for shop, url in links)
    await message.answer("\n".join(lines), disable_web_page_preview=True)

@dp.message(Command("compare"))
async def compare_command(message: Message):
    await message.answer(
        "Send two product URLs in one message, each on its own line. I will try to read verified page metadata and compare prices if both pages provide them. Exact product matching is best-effort, so check model/size/variant before buying."
    )

@dp.message(Command("history"))
async def history_command(message: Message):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Use: <code>/history ID</code> (example: <code>/history 3</code>)")
        return
    rows = db.get_price_history(message.from_user.id, int(parts[1]), 10)
    if not rows:
        await message.answer("No price history yet. A verified price must be found during a check first.")
        return
    lines = [f"<b>📉 Price history for item #{int(parts[1])}</b>"]
    for row in rows:
        lines.append(f"• {html.escape(row['checked_at'])}: <b>{row['price']:.2f} {html.escape(row['currency'] or '')}</b>")
    await message.answer("\n".join(lines))

@dp.message(Command("delete"))
async def delete_command(message: Message):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Use: <code>/delete ID</code> (example: <code>/delete 3</code>)")
        return
    deleted = db.delete_product(message.from_user.id, int(parts[1]))
    await message.answer("Deleted." if deleted else "I couldn't find that saved item.")

@dp.callback_query(F.data == "list")
async def callback_list(callback: CallbackQuery):
    await callback.answer()
    await show_products(callback.message)

@dp.callback_query(F.data == "help_check")
async def callback_check(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("Send the full product URL here. I will save it and report whether a verified adapter is available.")

@dp.callback_query(F.data == "compare_help")
async def callback_compare(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("Use /compare, then send two product URLs on separate lines.")

@dp.callback_query(F.data == "about")
async def callback_about(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "<b>Features</b>\n"
        "• Save, list, and delete product links\n• Product metadata adapters for Amazon India, Flipkart, and Meesho\n"
        "• /find creates shop search links for possible same-product listings\n• /compare attempts a verified metadata/price comparison for two links\n"
        "• Price history with /history ID\n• Periodic price checks and notifications when a verified price drops\n"
        "• Local SQLite database; no AI API key or external database\n\n"
        "<b>Limits</b>\n"
        "Exact product matching, coupons, and live prices are not guaranteed. Alerts require a price to be successfully read, and the bot must remain online."
    )

@dp.message(F.text)
async def handle_text(message: Message):
    text = (message.text or "").strip()
    if text.startswith("/"):
        await message.answer("Unknown command. Use /help.")
        return
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) == 2 and all(line.startswith(("http://", "https://")) for line in lines):
        validated = [validate_product_url(line) for line in lines]
        if not all(ok for ok, _ in validated):
            await message.answer("One or both links failed validation. Please send valid public product URLs.")
            return
        await message.answer("Checking both links for public product metadata…")
        import asyncio
        first, second = await asyncio.gather(registry.inspect(validated[0][1]), registry.inspect(validated[1][1]))
        title_a = first.title or "Unknown product"
        title_b = second.title or "Unknown product"
        norm = lambda value: re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
        similarity = SequenceMatcher(None, norm(title_a), norm(title_b)).ratio()
        lines = ["<b>⚖️ Product comparison</b>"]
        for index, item in enumerate((first, second), 1):
            price_text = f"{item.price:.2f} {item.currency or ''}" if item.price is not None else "Not verified"
            lines.append(
                f"\n<b>{index}. {html.escape(item.shop)}</b>\n"
                f"Product: {html.escape(item.title)}\nPrice: <b>{html.escape(price_text)}</b>\n"
                f'<a href="{html.escape(item.product_url, quote=True)}">Open listing</a>\n'
                f"{html.escape(item.note or '')}"
            )
        if similarity >= 0.72:
            lines.append("\n🟡 Titles look similar, but verify model, size, colour, and seller manually.")
        else:
            lines.append("\n⚠️ Titles differ. These may not be the same product, so price comparison may be unfair.")
        if first.price is not None and second.price is not None and first.currency and second.currency and first.currency == second.currency:
            cheaper = first if first.price < second.price else second if second.price < first.price else None
            if cheaper:
                lines.append(f"\n💰 Lower listed price: <b>{html.escape(cheaper.shop)}</b> by {abs(first.price-second.price):.2f} {html.escape(first.currency or second.currency or 'INR')}.")
            else:
                lines.append("\n💰 Both listings show the same price.")
        else:
            lines.append("\nPrice winner unavailable: one or both pages did not expose a verified comparable price.")
        await message.answer("\n".join(lines), disable_web_page_preview=True)
        return
    if len(lines) != 1:
        await message.answer("Send one product URL to save it, or use /compare and send two URLs on separate lines.")
        return
    ok, result = validate_product_url(lines[0])
    if not ok:
        await message.answer(result)
        return
    added, product_id = db.add_product(message.from_user.id, result, settings.max_links_per_user)
    if product_id is None:
        await message.answer(f"You've reached the limit of {settings.max_links_per_user} saved links.")
        return
    if not added:
        await message.answer(f"That link is already saved as item #{product_id}. Use /products to see your list.")
        return
    snapshot = await registry.inspect(result)
    # Record the first verified price immediately as the tracking baseline.
    if snapshot.price is not None:
        db.save_price(
            int(product_id), float(snapshot.price), snapshot.currency or "INR",
            snapshot.title, snapshot.shop,
        )
    # Show only fields actually found in the product page metadata.
    host = urlparse(result).hostname or "unknown"
    await message.answer(
        f"✅ Saved as item <b>#{product_id}</b>.\n"
        f"Website: <code>{html.escape(host)}</code>\n\n"
        f"Product: <b>{html.escape(snapshot.title)}</b>\n"
        + (f"Price found: <b>{snapshot.price:.2f} {html.escape(snapshot.currency or '')}</b>\n" if snapshot.price is not None else "Price: <i>not verified</i>\n")
        + f"\n{html.escape(snapshot.note or 'No live price was retrieved.')}\n\n"
        + "Use /products to view saved links. Any displayed price is read from page metadata and can change."
    )

async def scheduled_check():
    """Check saved links; notify only when a previously verified price drops."""
    rows = db.list_all_products()
    for row in rows:
        snapshot = await registry.inspect(row["url"])
        if snapshot.price is None:
            continue
        previous = db.save_price(
            int(row["id"]), float(snapshot.price), snapshot.currency or "INR",
            snapshot.title, snapshot.shop,
        )
        # First successful price becomes a baseline; later drops trigger a message.
        if previous is not None and snapshot.price < previous:
            old = f"{previous:.2f} {snapshot.currency or 'INR'}"
            new = f"{snapshot.price:.2f} {snapshot.currency or 'INR'}"
            try:
                await bot.send_message(
                    int(row["user_id"]),
                    f"📉 <b>Price drop detected!</b>\n"
                    f"{html.escape(snapshot.title)}\n"
                    f"Previous verified price: <s>{old}</s>\n"
                    f"New verified price: <b>{new}</b>\n"
                    f'<a href="{html.escape(snapshot.product_url, quote=True)}">Open product</a>',
                    disable_web_page_preview=True,
                )
            except Exception:
                # One user's blocked bot must not stop the rest of the checks.
                continue

async def main():
    scheduler = build_scheduler(settings.check_interval_minutes, scheduled_check)
    scheduler.start()
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
