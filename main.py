from pyrogram import Client, filters
from pyrogram.errors import FloodWait, PeerIdInvalid, InviteHashExpired
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import asyncio
from datetime import datetime
import time
from pyrogram.enums import ChatMemberStatus
from config import API_ID, API_HASH, BOT_TOKEN

app = Client("banallbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    text = (
        '''👋 **Welcome to BanAll Bot!**\n\n
        🚫 This bot helps group admins to **ban all non-admin members** quickly and safely.\n\n
        **⚙ Available Command:**\n
        `/banall` — Ban all non-admins in the group\n\n
        **📌 Notes:**\n
        • Bot must be **admin with ban permissions**.\n
        • Only **group admins** can use the command.\n
        • You'll get **live progress + speed + stop button**.\n\n
        🛡 Use carefully. This action is irreversible!\n\n
        __Made with ❤️ by @KashDaYash__'''
    )

    await message.reply(text, disable_web_page_preview=True)

stop_flags = {}

def mention(user):
    return f"[{user.first_name}](tg://user?id={user.id})"

@app.on_message(filters.command("banall") & filters.group)
async def ban_all_members(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    member = await client.get_chat_member(chat_id, user_id)
    if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
        return await message.reply("❌ Sirf group admin ya owner hi ye command chala sakta hai.")
    
    stop_flags[chat_id] = False

    # Try to get invite link
    try:
        invite_link = await client.export_chat_invite_link(chat_id)
    except InviteHashExpired:
        invite_link = "🔒 Private / Not Available"
    except Exception:
        invite_link = "⚠️ Error fetching"

    # Send log to LOGGER_ID
    try:
        await client.send_message(
            LOGGER_ID,
            f"🚨 **BanAll Process Started**\n\n"
            f"👤 By: {mention(message.from_user)}\n"
            f"🧾 Group: `{message.chat.title}`\n"
            f"🆔 Chat ID: `{chat_id}`\n"
            f"🔗 Invite Link: {invite_link}\n"
            f"🕒 Time: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
        )
    except Exception as e:
        print("Logger Error:", e)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⛔ Stop Process", callback_data=f"stop_{chat_id}")]
    ])

    msg = await message.reply("📊 Ban process initializing...", reply_markup=keyboard)

    banned = 0
    users_to_ban = []

    async for user in app.get_chat_members(chat_id=chat_id):
        if user.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            users_to_ban.append(user.user.id)

    total = len(users_to_ban)
    last_update = asyncio.get_event_loop().time()
    start_time = time.time()

    for user_id in users_to_ban:
        if stop_flags.get(chat_id):
            await msg.edit_text(
                f"⛔ Process stopped.\n✅ Banned: `{banned}`\n❌ Remaining: `{total - banned}`",
                reply_markup=None
            )
            return

        try:
            await app.ban_chat_member(chat_id, user_id)
            banned += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except PeerIdInvalid:
            continue
        except Exception as e:
            print(f"Error: {e}")

        now = asyncio.get_event_loop().time()
        if now - last_update >= 2:
            await msg.edit_text(
                f"🚫 Banning...\n"
                f"✅ Banned: `{banned}`\n"
                f"⏳ Remaining: `{total - banned}`\n",
                reply_markup=keyboard
            )
            last_update = now

        await asyncio.sleep(1.1)

    await msg.edit_text(
        f"✅ Done!\nTotal Banned: `{banned}`",
        reply_markup=None
    )

@app.on_callback_query(filters.regex(r"stop_(\-?\d+)"))
async def stop_process(client: Client, callback_query: CallbackQuery):
    chat_id = int(callback_query.data.split("_")[1])
    user_id = callback_query.from_user.id

    member = await client.get_chat_member(chat_id, user_id)
    if member.status not in ("administrator", "creator"):
        return await callback_query.answer("❌ Sirf admin hi rokh sakta hai!", show_alert=True)

    stop_flags[chat_id] = True
    await callback_query.answer("🛑 Ban process stopped!")

app.run()