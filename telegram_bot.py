import os
import json
import urllib.parse
import urllib.request
import urllib.error

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BASE_URL = os.environ.get("API_URL", "http://notessub.duckdns.org/")
TIMEOUT = float(os.environ.get("API_TIMEOUT", "30"))
BOT_TOKEN = os.environ.get("8957125282:AAEoJL6Qd3WWcslxwVUZK2wRJHNPWARoDmQ")

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
    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "Send the number you want to use.\n"
        "Example: 9876543210"
    )
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

        await update.message.reply_text(
            f"✅ {message}\n\n"
            "Now send the OTP you received."
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
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_number)
            ],
            OTP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_otp)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conversation)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
