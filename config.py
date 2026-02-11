import os
from os import getenv

API_ID = int(os.environ.get("API_ID", "22518279"))  # Replace with your actual api_id or use .env
API_HASH = os.environ.get("API_HASH", "61e5cc94bc5e6318643707054e54caf4")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8006527414:AAG9FvwPFf3ozLwe5W_PYnb-LNxH4JE86wU")

OWNER_ID = int(os.environ.get("OWNER_ID", "8500852075"))  # Your Telegram user ID

# Fixed SUDO_USERS parsing - handles empty strings properly
sudo_users_str = os.environ.get("SUDO_USERS", "")
if sudo_users_str:
    SUDO_USERS = list(map(int, sudo_users_str.split()))
else:
    SUDO_USERS = []

MONGO_URL = os.environ.get("MONGO_URL", "mongodb+srv://<sandeepsharma786>:<Sandeep786>@cluster0.xz78w44.mongodb.net")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1003533276261"))  # Telegram channel ID (with -100 prefix)
PREMIUM_LOGS = os.environ.get("PREMIUM_LOGS", "-1003828380273")  # Optional here you'll get all logs
