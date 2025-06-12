import sqlite3
import re

# 1. Проверяем какой телефон в истории диалогов
user_id = 768238543  # Ваш реальный ID

conn = sqlite3.connect('restaurant.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT message_text FROM conversations 
    WHERE user_id = ? 
    ORDER BY timestamp DESC 
    LIMIT 10
""", (user_id,))

messages = [row[0] for row in cursor.fetchall()]
conn.close()

print("Последние сообщения:")
for i, msg in enumerate(messages):
    print(f"{i+1}. {msg}")

print("\nИщем телефон в сообщениях:")
user_phone = None
for message in messages:
    phone_match = re.search(r'\+?\d[\d\s\-\(\)]{9,}', message)
    if phone_match:
        user_phone = re.sub(r'[\s\-\(\)]', '', phone_match.group(0))
        print(f"✅ Найден телефон: {user_phone} в сообщении: '{message}'")
        break

if not user_phone:
    print("❌ Телефон НЕ найден в истории диалогов!")
else:
    print(f"\n2. Проверяем бронирования для телефона: {user_phone}")
    from ai_tools import AITools
    tools = AITools()
    bookings = tools.get_user_bookings(user_phone)
    print(f"Найдено бронирований: {len(bookings)}")
    for booking in bookings:
        print(f"  #{booking['id']}: {booking['date']} {booking['time']}")