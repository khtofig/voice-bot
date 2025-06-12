import sqlite3
import re

def get_booking_in_progress(user_id):
    """Получить незавершенное бронирование пользователя"""
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
    
    # Собираем данные из всех сообщений
    booking_data = {}
    
    for msg in messages:
        print(f"Анализирую: '{msg}'")
        
        # Ищем имя
        name_match = re.search(r'меня зовут\s+(\w+)|на имя\s+(\w+)', msg, re.IGNORECASE)
        if name_match:
            name = (name_match.group(1) or name_match.group(2)).capitalize()
            booking_data['name'] = name
            print(f"  ✅ Найдено имя: {name}")
        
        # Ищем телефон
        phone_match = re.search(r'\+?\d[\d\s\-\(\)]{9,}', msg)
        if phone_match:
            phone = re.sub(r'[\s\-\(\)]', '', phone_match.group(0))
            booking_data['phone'] = phone
            print(f"  ✅ Найден телефон: {phone}")
        
        # Ищем количество гостей
        guests_match = re.search(r'(\d+)\s*чел|(\d+)\s*человек|будет\s+(\d+)|на\s+(\d+)', msg, re.IGNORECASE)
        if guests_match:
            guests_str = guests_match.group(1) or guests_match.group(2) or guests_match.group(3) or guests_match.group(4)
            guests = int(guests_str)
            if 1 <= guests <= 20:
                booking_data['guests'] = guests
                print(f"  ✅ Найдено гостей: {guests}")
    
    return booking_data

# Тестируем с реальным ID
result = get_booking_in_progress(768238543)
print("\n" + "="*50)
print("ИТОГОВЫЕ СОБРАННЫЕ ДАННЫЕ:")
print(result)

# Проверяем что нужно еще
required = ['name', 'phone', 'guests']
missing = [field for field in required if field not in result]
print(f"Недостает: {missing}")

if not missing:
    print("🎉 ВСЕ ДАННЫЕ ЕСТЬ! Можно создавать бронирование!")