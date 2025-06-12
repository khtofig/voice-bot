import sqlite3

conn = sqlite3.connect('restaurant.db')
cursor = conn.cursor()

#test
# Создаем таблицу бронирований
cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        restaurant_id INTEGER,
        customer_name TEXT NOT NULL,
        customer_phone TEXT NOT NULL,
        booking_date DATE NOT NULL,
        booking_time TIME NOT NULL,
        guests_count INTEGER NOT NULL,
        status TEXT DEFAULT 'новое',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (restaurant_id) REFERENCES restaurants (id)
    )
""")

# Добавляем тестовые бронирования
test_bookings = [
    (1, 'Иван Петров', '+7-905-123-4567', '2025-06-15', '19:00', 4, 'подтверждено', 'Столик у окна'),
    (1, 'Мария Сидорова', '+7-916-987-6543', '2025-06-15', '20:30', 2, 'новое', ''),
    (1, 'Алексей Иванов', '+7-925-555-1234', '2025-06-16', '18:00', 6, 'новое', 'День рождения')
]

cursor.executemany("""
    INSERT INTO bookings (restaurant_id, customer_name, customer_phone, booking_date, booking_time, guests_count, status, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", test_bookings)

conn.commit()
conn.close()

print("Таблица бронирований создана с тестовыми данными!")