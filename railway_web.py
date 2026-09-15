import os
import json
import urllib.parse
import urllib.request
import urllib.error

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BASE_URL = os.environ.get("API_URL", "http://notessub.duckdns.org/")
TIMEOUT = float(os.environ.get("API_TIMEOUT", "30"))
BOT_TOKEN = os.environ.get("BOT_TOKEN")

NUMBER, OTP = range(2)


def api_request(number, otp=None):
    params = {"number": number}
    if otp is not None:
        params["otp"] = otp

    separator = "&" if "?" in BASE_URL else "?"
    url = BASE_URL + separator + urllib.parse.urlencode(params)

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "NotesSub-Telegram-Bot/1.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        raw = response.read().decode("utf-8", errors="replace")

    return json.loads(raw)


def find_link(data):
    if isinstance(data, dict):
        for key in ("unique_link", "link"):
            value = data.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                return value

        for value in data.values():
            result = find_link(value)
            if result:
                return result

    elif isinstance(data, list):
        for item in data:
            result = find_link(item)
            if result:
                return result

    return None


def save_link(link):
    with open("links.txt", "a", encoding="utf-8") as f:
        f.write(link.rstrip("\r\n") + "\n")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("🚀 Get Started", callback_data="start_number")],
        [
            InlineKeyboardButton("ℹ️ Help", callback_data="help"),
            InlineKeyboardButton("👑 Owner", url="https://t.me/Momy_A1"),
        ],
    ]
    await update.message.reply_text(
        "╭━━━━━━━━━━━━━━━━━━╮\n"
        "   👑 *PREMIUM BOT*\n"
        "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        "✨ Welcome!\n"
        "⚡ Fast • Simple • Premium\n\n"
        "👤 Owner: @Momy_A1\n\n"
        "Tap *Get Started* to continue.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return NUMBER


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "start_number":
        context.user_data.clear()
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_menu")]]
        await query.edit_message_text(
            "📱 *Enter your number*\n\nSend the number to continue.\n\n⚠️ *Only Jio number will work.*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return NUMBER
    if query.data == "back_menu":
        keyboard = [
            [InlineKeyboardButton("🚀 Get Started", callback_data="start_number")],
            [
                InlineKeyboardButton("ℹ️ Help", callback_data="help"),
                InlineKeyboardButton("👑 Owner", url="https://t.me/Momy_A1"),
            ],
        ]
        await query.edit_message_text(
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            "   👑 *PREMIUM BOT*\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "✨ Welcome!\n"
            "⚡ Fast • Simple • Premium\n\n"
            "👤 Owner: @Momy_A1\n\n"
            "Tap *Get Started* to continue.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        context.user_data.clear()
        return NUMBER
    if query.data == "back_number":
        context.user_data.pop("number", None)
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_menu")]]
        await query.edit_message_text(
            "📱 *Enter your number*\n\nSend the number to continue.\n\n⚠️ *Only Jio number will work.*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return NUMBER
    if query.data == "help":
        await query.answer(
            "Use Get Started, then follow the bot's instructions.",
            show_alert=True,
        )
        return NUMBER
    return NUMBER


async def receive_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    number = update.message.text.strip()

    if not number:
        await update.message.reply_text("❌ Number cannot be empty. Send it again.")
        return NUMBER

    context.user_data["number"] = number

    await update.message.reply_text("⏳ Sending OTP...")

    try:
        response = api_request(number)

        message = "OTP request completed."
        if isinstance(response, dict) and response.get("message"):
            message = str(response["message"])

        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_number")]]
        await update.message.reply_text(
            f"✅ {message}\n\n"
            "Now send the OTP you received.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return OTP

    except Exception as exc:
        await update.message.reply_text(f"❌ API request failed: {exc}")
        return ConversationHandler.END


async def receive_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp = update.message.text.strip()
    number = context.user_data.get("number")

    if not number:
        await update.message.reply_text("Session expired. Send /start and try again.")
        return ConversationHandler.END

    if not otp:
        await update.message.reply_text("❌ OTP cannot be empty. Send it again.")
        return OTP

    await update.message.reply_text("⏳ Verifying OTP...")

    try:
        response = api_request(number, otp)
        link = find_link(response)

        if link:
            save_link(link)
            await update.message.reply_text(
                "✅ OTP verification completed.\n\n"
                f"🔗 Your link:\n{link}"
            )
        else:
            await update.message.reply_text(
                "⚠️ API response received, but no link was found.\n\n"
                + json.dumps(response, indent=2, ensure_ascii=False)
            )

    except Exception as exc:
        await update.message.reply_text(f"❌ OTP verification failed: {exc}")

    finally:
        context.user_data.clear()

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Cancelled. Send /start to begin again.")
    return ConversationHandler.END


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing.")

    app = Application.builder().token(BOT_TOKEN).build()

    conversation = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NUMBER: [
                CommandHandler("start", start),
                CallbackQueryHandler(button_handler, pattern=r"^(start_number|help|back_menu)$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_number),
            ],
            OTP: [
                CommandHandler("start", start),
                CallbackQueryHandler(button_handler, pattern=r"^(back_number|back_menu)$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_otp),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conversation)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
