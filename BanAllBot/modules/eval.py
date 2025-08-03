import sys
import traceback
import io
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from BanAllBot import app
from config import OWNER_ID, LOGGER_ID

IKM = InlineKeyboardMarkup
IKB = InlineKeyboardButton
CHAT_ID = LOGGER_ID

def excl(cmd, prefixes=['/', '.', '!'], cs=True):
    return filters.command(cmd, prefixes, cs) & (filters.group | filters.channel | filters.private)

# Execute async code dynamically
async def aexec_(code, smessatatus, client):
    m = message = event = smessatatus
    p = lambda _x: print(_x)
    exec("async def __aexec(message, event, m, client, p): " +
         "".join(f"\n {l}" for l in code.split("\n")))
    return await locals()["__aexec"](message, event, m, client, p)

# Eval command
@app.on_edited_message(excl('eval'))
@app.on_message(excl('eval'))
async def eval_handler(client, message: Message):
    if message.from_user.id != OWNER_ID:
        return

    if len(message.command) == 1:
        return await message.reply("❓ What do you want to run?")

    cmd = "".join(message.text.split(None, 1)[1:])
    if "config.py" in cmd:
        return await message.reply_text("🚫 Access to config.py is restricted.", reply_to_message_id=message.id)

    eva = await message.reply_text("🌀 Running...", reply_to_message_id=message.id)
    old_stderr = sys.stderr
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    redirected_error = sys.stderr = io.StringIO()
    stdout = stderr = exc = None

    try:
        await aexec_(cmd, message, client)
    except Exception:
        exc = traceback.format_exc()

    stdout = redirected_output.getvalue()
    stderr = redirected_error.getvalue()
    sys.stdout = old_stdout
    sys.stderr = old_stderr

    evaluation = exc or stderr or stdout or "✅ Success"
    final_output = f"⥤ ᴇᴠᴀʟ : \n<pre>{cmd}</pre>\n\n⥤ ʀᴇsᴜʟᴛ : \n<pre>{evaluation}</pre>"

    keyboard = IKM([[IKB("🗑", callback_data="evclose")]])

    if len(final_output) > 4096:
        filename = "result.txt"
        with open(filename, "w+", encoding="utf8") as out_file:
            out_file.write(str(evaluation.strip()))

        await message.reply_document(
            document=filename,
            caption=f"**INPUT:**\n`{cmd[:980]}`\n\n**OUTPUT:**\n`Attached Document`",
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.MARKDOWN
        )
        await eva.delete()
        os.remove(filename)
    else:
        await eva.edit_text(final_output, reply_markup=keyboard)

# Close button callback
@app.on_callback_query(filters.regex('^evclose$'), group=50)
async def close_eval_result(client, q: CallbackQuery):
    if q.from_user.id != q.message.reply_to_message.from_user.id:
        return
    await q.message.delete()