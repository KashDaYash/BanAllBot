import sqlite3
from threading import RLock

DB_PATH = "BanAllBot/database/guard.db"
LOCK = RLock()

def init_guard_db():
    with LOCK, sqlite3.connect(DB_PATH) as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS guard_chats (
            chat_id INTEGER PRIMARY KEY
        )""")
        db.commit()

def is_guard_enabled(chat_id: int) -> bool:
    with LOCK, sqlite3.connect(DB_PATH) as db:
        cur = db.execute("SELECT 1 FROM guard_chats WHERE chat_id = ?", (chat_id,))
        return cur.fetchone() is not None

def enable_guard(chat_id: int):
    with LOCK, sqlite3.connect(DB_PATH) as db:
        db.execute("INSERT OR IGNORE INTO guard_chats (chat_id) VALUES (?)", (chat_id,))
        db.commit()

def disable_guard(chat_id: int):
    with LOCK, sqlite3.connect(DB_PATH) as db:
        db.execute("DELETE FROM guard_chats WHERE chat_id = ?", (chat_id,))
        db.commit()

def all_guarded_chats() -> list[int]:
    with LOCK, sqlite3.connect(DB_PATH) as db:
        cur = db.execute("SELECT chat_id FROM guard_chats")
        return [row[0] for row in cur.fetchall()]