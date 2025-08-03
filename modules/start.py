from pyrogram import Client, filters
from pyrogram.types import Message
from BanAllBot import app
from config import LOGGER_ID
from BanAllBot.database.user import add_user

@app.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    user = message.from_user
    add_user(user.id, user.first_name, user.mention)

    await app.send_message(LOGGER_ID, f"{user.mention} started bot\nUser ID: {user.id}")

    text = (
        '''👋 **Welcome to BanAll Bot!**\n\n
        🚫 This bot helps group admins to **ban all non-admin members** quickly and safely.\n\n
        **⚙ Available Command:**\n
        `/banall` — Ban all non-admins in the group\n\n
        `/ban` — Ban a non-admin in the group\n\n
        **📌 Notes:**\n
        • Bot must be **admin with ban permissions**.\n
        • Only **group admins** can use the command.\n
        • You'll get **live progress + speed + stop button**.\n\n
        🛡 Use carefully. This action is irreversible!\n\n
        __Made with ❤️ by @KashDaYash__'''
    )

    await message.reply(text, disable_web_page_preview=True)