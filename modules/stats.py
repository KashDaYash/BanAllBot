from pyrogram import Client, filters
from pyrogram.types import Message
from BanAllBot import app
from config import OWNER_ID
from BanAllBot.database.user import total_users

@app.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def show_stats(client: Client, message: Message):
    count = total_users()
    await message.reply(f"👥 Total users: **{count}**")