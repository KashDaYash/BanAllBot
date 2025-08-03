from pyrogram import filters, idle
import os
from BanAllBot import app
from config import LOGGER_ID 
from BanAllBot.database.guard import init_guard_db
from BanAllBot.database.user import init_user_db

# Load all plugins in modules folder
def load_plugins():
    path = "BanAllBot/modules"
    for filename in os.listdir(path):
        if filename.endswith(".py"):
            module = f"BanAllBot.modules.{filename[:-3]}"
            __import__(module)

if __name__ == "__main__":
    load_plugins()
    init_guard_db()
    init_user_db()
    print("✅ All plugins loaded.")
    app.start()
    app.send_message(chat_id=LOGGER_ID, text=f"{(app.get_me()).mention} Started 💫")
    idle()