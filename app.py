from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN
import uvloop 


uvloop.install()
app = Client(
    "banallbot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=4,
)