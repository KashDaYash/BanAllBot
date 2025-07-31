from pyrogram import Client, filters
from config import API_ID, API_HASH, BOT_TOKEN

app = Client("banallbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
def start(client, message):
    message.reply("Hello! I am BanAllBot. Add me to a group and promote as admin to use mass-ban features.")

@app.on_message(filters.command("banall") & filters.group)
def banall(client, message):
    if message.from_user and message.from_user.id in [admin.user.id for admin in client.get_chat_administrators(message.chat.id)]:
        for member in client.get_chat_members(message.chat.id):
            try:
                if not member.user.is_bot:
                    client.ban_chat_member(message.chat.id, member.user.id)
            except Exception:
                continue
        message.reply("Ban-all operation completed.")
    else:
        message.reply("You must be an admin to use this command.")

app.run()