import asyncio
import logging
from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN

logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s",
    level=logging.INFO,
)

# Create the Client but DON'T start it here
app = Client(
    ":Extractor:",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    sleep_threshold=120,
    workers=200
)

# REMOVED: Auto-start code that was causing issues
# The client should be started in __main__.py only
# loop = asyncio.get_event_loop()
# loop.run_until_complete(info_bot())
