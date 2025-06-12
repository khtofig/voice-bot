import sqlite3

conn = sqlite3.connect('restaurant.db')
cursor = conn.cursor()

# Добавляем недостающие колонки в таблицу restaurants
cursor.execute("ALTER TABLE restaurants ADD COLUMN greeting_message TEXT DEFAULT 'Здравствуйте! Вас приветствует наш ресторан.'")
cursor.execute("ALTER TABLE restaurants ADD COLUMN ai_personality TEXT DEFAULT 'Ты дружелюбный помощник ресторана.'")

# Исправляем menu_items где restaurant_id = None
cursor.execute("UPDATE menu_items SET restaurant_id = 1 WHERE restaurant_id IS NULL")

conn.commit()
conn.close()

print("База данных обновлена!")