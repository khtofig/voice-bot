import sqlite3

conn = sqlite3.connect('restaurant.db')
cursor = conn.cursor()

# Смотрим какие user_id есть в базе
cursor.execute("SELECT DISTINCT user_id, user_name FROM conversations")
users = cursor.fetchall()

print("Пользователи в базе:")
for user_id, user_name in users:
    print(f"ID: {user_id}, Имя: {user_name}")

# Берем первого пользователя и тестируем
if users:
    real_user_id = users[0][0]
    print(f"\nТестируем с real_user_id: {real_user_id}")
    
    cursor.execute("""
        SELECT message_text FROM conversations 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 10
    """, (real_user_id,))
    
    messages = [row[0] for row in cursor.fetchall()]
    print("Последние сообщения:")
    for msg in messages:
        print(f"- {msg}")

conn.close()