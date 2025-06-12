import sqlite3

conn = sqlite3.connect('restaurant.db')
cursor = conn.cursor()

# Создаем таблицу столиков
cursor.execute("""
    CREATE TABLE IF NOT EXISTS tables (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        restaurant_id INTEGER,
        table_number TEXT NOT NULL,
        seats_count INTEGER NOT NULL,
        location_type TEXT,
        description TEXT,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (restaurant_id) REFERENCES restaurants (id)
    )
""")

# Добавляем поля в таблицу бронирований
cursor.execute("ALTER TABLE bookings ADD COLUMN table_id INTEGER")
cursor.execute("ALTER TABLE bookings ADD COLUMN special_requests TEXT")

# Добавляем тестовые столики
test_tables = [
    (1, '1', 2, 'window', 'Уютный столик у большого окна с видом на улицу', 'active'),
    (1, '2', 4, 'window', 'Столик для 4 человек у панорамного окна', 'active'),
    (1, '3', 6, 'center', 'Большой стол в центре зала для компаний', 'active'),
    (1, '4', 2, 'quiet', 'Тихий столик в спокойной зоне', 'active'),
    (1, '5', 8, 'vip', 'VIP столик для важных гостей', 'active'),
    (1, '6', 4, 'stage', 'Столик рядом со сценой для любителей живой музыки', 'active'),
    (1, '7', 2, 'bar', 'Столик у барной стойки', 'active'),
    (1, '8', 6, 'terrace', 'Летняя терраса (сезонный)', 'active'),
    (1, '9', 4, 'center', 'Стандартный столик в основном зале', 'active'),
    (1, '10', 10, 'banquet', 'Банкетный стол для больших компаний', 'active')
]

cursor.executemany("""
    INSERT INTO tables (restaurant_id, table_number, seats_count, location_type, description, status)
    VALUES (?, ?, ?, ?, ?, ?)
""", test_tables)

conn.commit()
conn.close()

print("✅ Таблица столиков создана!")
print("✅ Добавлены поля в таблицу бронирований!")
print("✅ Загружены 10 тестовых столиков:")
print("   • 2 столика у окна (2 и 4 места)")
print("   • 2 в центре зала (4 и 6 мест)")
print("   • 1 VIP столик (8 мест)")
print("   • 1 у сцены (4 места)")
print("   • 1 в тихой зоне (2 места)")
print("   • 1 у бара (2 места)")
print("   • 1 на террасе (6 мест)")
print("   • 1 банкетный (10 мест)")