import sqlite3
import os

def reset_database():
    """Полная пересборка базы данных"""
    
    # Удаляем старую базу
    if os.path.exists('restaurant.db'):
        os.remove('restaurant.db')
        print("🗑️ Старая база данных удалена")
    
    # Создаем новую базу
    conn = sqlite3.connect('restaurant.db')
    cursor = conn.cursor()
    
    # Создаем все таблицы заново
    tables = [
        # Рестораны
        """
        CREATE TABLE restaurants (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            working_hours TEXT,
            greeting_message TEXT DEFAULT 'Здравствуйте! Вас приветствует наш ресторан.',
            ai_personality TEXT DEFAULT 'Ты дружелюбный помощник ресторана.',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Столики
        """
        CREATE TABLE tables (
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
        """,
        
        # Меню
        """
        CREATE TABLE menu_items (
            id INTEGER PRIMARY KEY,
            restaurant_id INTEGER,
            category TEXT,
            name TEXT,
            description TEXT,
            price REAL,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants (id)
        )
        """,
        
        # Бронирования
        """
        CREATE TABLE bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER,
            table_id INTEGER,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            booking_date DATE NOT NULL,
            booking_time TIME NOT NULL,
            guests_count INTEGER NOT NULL,
            status TEXT DEFAULT 'новое',
            special_requests TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants (id),
            FOREIGN KEY (table_id) REFERENCES tables (id)
        )
        """,
        
        # Диалоги
        """
        CREATE TABLE conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            user_name TEXT,
            message_text TEXT NOT NULL,
            bot_response TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    ]
    
    # Создаем таблицы
    for table_sql in tables:
        cursor.execute(table_sql)
    
    # Добавляем демо-ресторан
    cursor.execute("""
        INSERT INTO restaurants (name, phone, address, working_hours, greeting_message, ai_personality)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        "Ресторан 'AI Вкусно'",
        "+994501234567", 
        "ул. Низами, 15",
        "10:00-23:00",
        "Здравствуйте! Спасибо что позвонили в ресторан 'AI Вкусно'. Я умный ИИ-помощник и помогу забронировать лучший столик!",
        "Ты умный и дружелюбный ИИ-помощник ресторана. Ты обязательно используешь функции для поиска столиков и создания бронирований. Ты помогаешь клиентам найти идеальный столик и всегда спрашиваешь недостающую информацию."
    ))
    
    # Добавляем столики
    test_tables = [
        (1, '1', 2, 'window', 'Романтический столик у большого окна с видом на улицу'),
        (1, '2', 4, 'window', 'Семейный столик у панорамного окна'),
        (1, '3', 6, 'center', 'Большой стол в центре зала для компаний'),
        (1, '4', 2, 'quiet', 'Уютный столик в тихой зоне для деловых встреч'),
        (1, '5', 8, 'vip', 'Премиум VIP столик для важных гостей'),
        (1, '6', 4, 'stage', 'Столик рядом со сценой для любителей живой музыки'),
        (1, '7', 2, 'bar', 'Барный столик для быстрого обеда'),
        (1, '8', 6, 'terrace', 'Летняя терраса с зеленью (сезонный)'),
        (1, '9', 4, 'center', 'Стандартный столик в основном зале'),
        (1, '10', 10, 'banquet', 'Банкетный стол для больших торжеств')
    ]
    
    cursor.executemany("""
        INSERT INTO tables (restaurant_id, table_number, seats_count, location_type, description)
        VALUES (?, ?, ?, ?, ?)
    """, test_tables)
    
    # Добавляем демо-меню
    menu_items = [
        (1, "Салаты", "Цезарь с курицей", "Классический салат с курицей, сыром и соусом", 650),
        (1, "Салаты", "Греческий салат", "Свежие овощи с сыром фета и оливками", 550),
        (1, "Горячие блюда", "Стейк Рибай", "Сочный говяжий стейк средней прожарки", 1200),
        (1, "Горячие блюда", "Паста Карбонара", "Классическая паста с беконом и сливочным соусом", 850),
        (1, "Горячие блюда", "Лосось на гриле", "Филе лосося с овощами", 950),
        (1, "Супы", "Борщ украинский", "Традиционный борщ с мясом", 450),
        (1, "Десерты", "Тирамису", "Классический итальянский десерт", 380),
        (1, "Напитки", "Домашний лимонад", "Свежий лимонад с мятой", 250),
        (1, "Напитки", "Кофе эспрессо", "Ароматный итальянский кофе", 180)
    ]
    
    cursor.executemany("""
        INSERT INTO menu_items (restaurant_id, category, name, description, price)
        VALUES (?, ?, ?, ?, ?)
    """, menu_items)
    
    conn.commit()
    conn.close()
    
    print("✅ Новая база данных создана!")
    print("🏪 Ресторан 'AI Вкусно' добавлен")
    print("🪑 10 столиков добавлено (у окна, VIP, тихие зоны)")
    print("🍽️ 9 блюд добавлено в меню")
    print("💬 История диалогов очищена")
    print("📋 Бронирования очищены")

if __name__ == "__main__":
    reset_database()