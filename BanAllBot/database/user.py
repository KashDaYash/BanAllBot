import sqlite3
from threading import RLock

DB_PATH = "BanAllBot/database/users.db"
LOCK = RLock()

def init_user_db():
    with LOCK, sqlite3.connect(DB_PATH) as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            mention TEXT
        )
        """)
        db.commit()

def add_user(user_id: int, name: str, mention: str):
    with LOCK, sqlite3.connect(DB_PATH) as db:
        db.execute("""
        INSERT OR IGNORE INTO users (user_id, name, mention)
        VALUES (?, ?, ?)
        """, (user_id, name, mention))
        db.commit()

def total_users() -> int:
    with LOCK, sqlite3.connect(DB_PATH) as db:
        cur = db.execute("SELECT COUNT(*) FROM users")
        return cur.fetchone()[0]