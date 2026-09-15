# Telegram Bot on Railway

Files:
- telegram_bot.py
- requirements.txt
- Procfile

Railway Variables:
- BOT_TOKEN = your Telegram bot token
- API_URL = optional; defaults to the API URL from the original script
- API_TIMEOUT = optional; defaults to 30

The bot flow is:
1. /start
2. User sends number
3. Bot requests OTP
4. User sends OTP
5. Bot verifies OTP and returns the link from the API response

Use only with your own/authorized API and accounts.
