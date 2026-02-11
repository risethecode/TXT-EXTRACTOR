import asyncio
import importlib
from pyrogram import idle
from Extractor import app
from Extractor.modules import ALL_MODULES

async def sumit_boot():
    """Initialize and run the bot"""
    # Start the client first
    await app.start()
    
    # Import all modules
    for all_module in ALL_MODULES:
        importlib.import_module("Extractor.modules." + all_module)
    
    print("» ʙᴏᴛ ᴅᴇᴘʟᴏʏ sᴜᴄᴄᴇssғᴜʟʟʏ ✨ 🎉")
    
    # Keep the bot running
    await idle()
    
    print("» ɢᴏᴏᴅ ʙʏᴇ ! sᴛᴏᴘᴘɪɴɢ ʙᴏᴛ.")

if __name__ == "__main__":
    asyncio.run(sumit_boot())
