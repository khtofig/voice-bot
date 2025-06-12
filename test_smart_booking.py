import sqlite3
import re
from datetime import datetime, timedelta

def get_booking_in_progress(user_id):
    """Получить незавершенное бронирование пользователя"""
    conn = sqlite3.connect('restaurant.db')
    cursor = conn.cursor()
    
    # Ищем последние сообщения пользователя
    cursor.execute("""
        SELECT message_text FROM conversations 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 10
    """, (user_id,))
    
    messages = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Собираем данные из всех сообщений
    booking_data = {}
    
    for msg in messages:
        # Ищем имя
        name_match = re.search(r'меня зовут\s+(\w+)|на имя\s+(\w+)', msg, re.IGNORECASE)
        if name_match:
            booking_data['name'] = (name_match.group(1) or name_match.group(2)).capitalize()
        
        # Ищем телефон
        phone_match = re.search(r'\+?\d[\d\s\-\(\)]{9,}', msg)
        if phone_match:
            booking_data['phone'] = re.sub(r'[\s\-\(\)]', '', phone_match.group(0))
        
        # Ищем количество гостей
        guests_match = re.search(r'(\d+)\s*чел|(\d+)\s*человек|будет\s+(\d+)', msg, re.IGNORECASE)
        if guests_match:
            guests = int(guests_match.group(1) or guests_match.group(2) or guests_match.group(3))
            if 1 <= guests <= 20:
                booking_data['guests'] = guests
    
    return booking_data

# Тестируем
user_id = 123  # Ваш telegram ID
result = get_booking_in_progress(user_id)
print("Собранные данные бронирования:")
print(result)

# Проверяем что нужно еще
required = ['name', 'phone', 'guests']
missing = [field for field in required if field not in result]
print(f"Недостает: {missing}")