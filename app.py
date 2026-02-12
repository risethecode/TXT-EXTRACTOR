import os
import threading
from flask import Flask
from pyrogram import Client, idle

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running successfully 🚀"

def run_bot():
    bot = Client(
        "ExtractorBot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN
    )
    bot.start()
    idle()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
