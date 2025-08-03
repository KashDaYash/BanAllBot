from pyrogram import filters, Client
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus
import re
from BanAllBot import app
from BanAllBot.database.guard import enable_guard, disable_guard, is_guard_enabled

@app.on_message(filters.command("nousername") & filters.group)
async def username_guard_cmd(client: Client, message: Message):
    user_status = await app.get_chat_member(message.chat.id, message.from_user.id)
    if user_status.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
        return await message.reply("❌ Sirf admins hi ye feature control kar sakte hain.")
    
    enabled = is_guard_enabled(message.chat.id)
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Enable", callback_data=f"usernameguard_enable_{message.chat.id}"),
            InlineKeyboardButton("❌ Disable", callback_data=f"usernameguard_disable_{message.chat.id}")
        ]
    ])

    status_text = (
        "🛡 Username Guard is currently **ENABLED** ✅"
        if enabled else
        "🛡 Username Guard is currently **DISABLED** ❌"
    )
    await message.reply(status_text, reply_markup=keyboard)

@app.on_callback_query(filters.regex(r"usernameguard_(enable|disable)_(\-?\d+)"))
async def toggle_username_guard(client: Client, query: CallbackQuery):
    action, chat_id = query.data.split("_")[1:]
    chat_id = int(chat_id)

    member = await app.get_chat_member(chat_id, query.from_user.id)
    if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
        return await query.answer("❌ Sirf admins hi ye kar sakte hain.", show_alert=True)

    if action == "enable":
        enable_guard(chat_id)
        await query.answer("✅ Username Guard enabled.")
        await query.message.edit_text("🛡 Username Guard is now **ENABLED** ✅")
    else:
        disable_guard(chat_id)
        await query.answer("❌ Username Guard disabled.")
        await query.message.edit_text("🛡 Username Guard is now **DISABLED** ❌")
        

@app.on_message(filters.text & filters.group)
async def auto_delete_non_member_usernames(client: Client, message: Message):
    if not is_guard_enabled(message.chat.id):
        return

    usernames = re.findall(r"@[\w\d_]{5,32}", message.text)
    if not usernames:
        return

    for uname in usernames:
        try:
            user = await client.get_users(uname)
            await client.get_chat_member(message.chat.id, user.id)
        except:
            try:
                await message.delete()
                return
            except:
                return        