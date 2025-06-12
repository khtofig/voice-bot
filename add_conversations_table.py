import sqlite3

conn = sqlite3.connect('restaurant.db')
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        user_name TEXT,
        message_text TEXT NOT NULL,
        bot_response TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

conn.commit()
conn.close()

print("✅ Таблица диалогов создана!")