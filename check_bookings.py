import sqlite3

conn = sqlite3.connect('restaurant.db')
cursor = conn.cursor()

print("Все бронирования:")
cursor.execute("SELECT * FROM bookings ORDER BY created_at DESC")
bookings = cursor.fetchall()
for booking in bookings:
    print(booking)

print("\nВсе диалоги:")
cursor.execute("SELECT user_name, message_text, bot_response, timestamp FROM conversations ORDER BY timestamp DESC LIMIT 10")
conversations = cursor.fetchall()
for conv in conversations:
    print(conv)

conn.close()