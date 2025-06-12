import sqlite3
from datetime import datetime

class RestaurantDatabase:
    def __init__(self, db_name='restaurant.db'):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Создание таблиц"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Таблица ресторанов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS restaurants (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                working_hours TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица настроек бота
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_settings (
                id INTEGER PRIMARY KEY,
                restaurant_id INTEGER,
                greeting_message TEXT,
                ai_personality TEXT,
                FOREIGN KEY (restaurant_id) REFERENCES restaurants (id)
            )
        ''')
        
        # Таблица меню
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS menu_items (
                id INTEGER PRIMARY KEY,
                restaurant_id INTEGER,
                category TEXT,
                name TEXT,
                description TEXT,
                price REAL,
                FOREIGN KEY (restaurant_id) REFERENCES restaurants (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("💾 База данных создана")
        
        # Добавляем демо-данные
        self.create_demo_data()
    
    def create_demo_data(self):
        """Создание демо-ресторана"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Проверяем есть ли рестораны
        cursor.execute('SELECT COUNT(*) FROM restaurants')
        if cursor.fetchone()[0] == 0:
            print("🍽️ Создаю демо-ресторан...")
            
            # Добавляем ресторан
            cursor.execute('''
                INSERT INTO restaurants (name, phone, address, working_hours)
                VALUES (?, ?, ?, ?)
            ''', ("Ресторан 'Вкусно'", "+994501234567", "ул. Низами, 15", "10:00-23:00"))
            
            restaurant_id = cursor.lastrowid
            
            # Настройки бота
            cursor.execute('''
                INSERT INTO bot_settings (restaurant_id, greeting_message, ai_personality)
                VALUES (?, ?, ?)
            ''', (restaurant_id, 
                 "Здравствуйте! Спасибо что позвонили в ресторан 'Вкусно'. Я помогу забронировать столик.",
                 "Вежливый и профессиональный администратор ресторана"))
            
            # Демо-меню
            menu_items = [
                ("Горячие блюда", "Паста Карбонара", "Классическая паста с беконом", 850),
                ("Горячие блюда", "Стейк Рибай", "Сочный стейк из говядины", 1200),
                ("Салаты", "Цезарь с курицей", "Салат с курицей и сыром", 600),
                ("Напитки", "Лимонад", "Домашний лимонад", 250)
            ]
            
            for category, name, description, price in menu_items:
                cursor.execute('''
                    INSERT INTO menu_items (restaurant_id, category, name, description, price)
                    VALUES (?, ?, ?, ?, ?)
                ''', (restaurant_id, category, name, description, price))
            
            conn.commit()
            print("✅ Демо-ресторан 'Вкусно' создан")
        
        conn.close()
    
    def get_restaurant_data(self, restaurant_id=1):
        """Получить данные ресторана"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.name, r.phone, r.address, r.working_hours, 
                   bs.greeting_message, bs.ai_personality
            FROM restaurants r
            LEFT JOIN bot_settings bs ON r.id = bs.restaurant_id
            WHERE r.id = ?
        ''', (restaurant_id,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    def get_menu_items(self, restaurant_id=1):
        """Получить меню"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT category, name, description, price 
            FROM menu_items 
            WHERE restaurant_id = ?
            ORDER BY category, name
        ''', (restaurant_id,))
        result = cursor.fetchall()
        conn.close()
        return result