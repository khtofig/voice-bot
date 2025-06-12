import sqlite3
import re
from datetime import datetime, timedelta

class AITools:
    """Инструменты для AI с поддержкой confidence scoring, fallback логики и работы со столиками"""
    
    def __init__(self, db_path='restaurant.db'):
        self.db_path = db_path
        
        # Fallback фразы для разных ситуаций
        self.fallback_phrases = {
            'low_confidence': [
                "Извините, не совсем понял. Можете повторить?",
                "Не расслышал последнее. Уточните, пожалуйста",
                "Простите, переспросите еще раз"
            ],
            'no_data': [
                "Минутку, проверяю информацию...",
                "Уточняю данные в системе...",
                "Проверяю наличие..."
            ],
            'complex_request': [
                "Это важный запрос. Передаю менеджеру",
                "Лучше уточнить детали у администратора",
                "Соединяю с нашим специалистом"
            ],
            'error': [
                "Произошла техническая ошибка. Минутку...",
                "Система обновляется. Попробуйте через минуту",
                "Передаю живому сотруднику"
            ]
        }

    # =============== ФУНКЦИИ РАБОТЫ СО СТОЛИКАМИ ===============
    
    def get_available_tables(self, date, time, guests_count, location_preference=None):
        """Получить доступные столики на дату и время"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Получаем все подходящие столики
            query = """
                SELECT t.id, t.table_number, t.seats_count, t.location_type, t.description
                FROM tables t
                WHERE t.restaurant_id = 1 
                AND t.status = 'active'
                AND t.seats_count >= ?
            """
            params = [guests_count]
            
            # Добавляем фильтр по типу расположения если указан
            if location_preference:
                query += " AND t.location_type = ?"
                params.append(location_preference)
            
            cursor.execute(query, params)
            all_tables = cursor.fetchall()
            
            # Проверяем какие столики заняты на указанное время
            cursor.execute("""
                SELECT DISTINCT table_id 
                FROM bookings 
                WHERE booking_date = ? 
                AND booking_time = ? 
                AND status != 'отменено'
                AND table_id IS NOT NULL
            """, (date, time))
            
            occupied_table_ids = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            # Фильтруем свободные столики
            available_tables = []
            for table in all_tables:
                table_id, number, seats, location, description = table
                if table_id not in occupied_table_ids:
                    available_tables.append({
                        'id': table_id,
                        'number': number,
                        'seats': seats,
                        'location': location,
                        'description': description
                    })
            
            print(f"🔍 Найдено {len(available_tables)} свободных столиков на {date} {time}")
            return available_tables
            
        except Exception as e:
            print(f"❌ Ошибка поиска столиков: {e}")
            return []
    
    def get_table_by_preference(self, date, time, guests_count, preference_text):
        """Найти столик по предпочтениям клиента"""
        try:
            # Определяем тип расположения по тексту клиента
            preference_mapping = {
                'окн': 'window',
                'вид': 'window', 
                'сцен': 'stage',
                'музык': 'stage',
                'тих': 'quiet',
                'спокой': 'quiet',
                'vip': 'vip',
                'вип': 'vip',
                'бар': 'bar',
                'террас': 'terrace',
                'банкет': 'banquet',
                'больш': 'banquet'
            }
            
            location_type = None
            preference_lower = preference_text.lower()
            
            for keyword, location in preference_mapping.items():
                if keyword in preference_lower:
                    location_type = location
                    break
            
            # Ищем столики с учетом предпочтений
            available_tables = self.get_available_tables(date, time, guests_count, location_type)
            
            if available_tables:
                print(f"✅ Найдены столики по предпочтению '{preference_text}': {len(available_tables)} вариантов")
                return available_tables
            else:
                print(f"❌ Столики по предпочтению '{preference_text}' не найдены")
                # Возвращаем любые доступные столики
                return self.get_available_tables(date, time, guests_count)
                
        except Exception as e:
            print(f"❌ Ошибка поиска по предпочтениям: {e}")
            return []
    
    def book_specific_table(self, table_id, customer_name, customer_phone, booking_date, booking_time, guests_count, special_requests=""):
        """Забронировать конкретный столик"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем доступность столика
            cursor.execute("""
                SELECT COUNT(*) FROM bookings 
                WHERE table_id = ? 
                AND booking_date = ? 
                AND booking_time = ? 
                AND status != 'отменено'
            """, (table_id, booking_date, booking_time))
            
            if cursor.fetchone()[0] > 0:
                conn.close()
                print(f"❌ Столик #{table_id} уже занят на {booking_date} {booking_time}")
                return None
            
            # Создаем бронирование с указанием столика
            cursor.execute("""
                INSERT INTO bookings 
                (restaurant_id, table_id, customer_name, customer_phone, booking_date, booking_time, guests_count, status, special_requests)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (1, table_id, customer_name, customer_phone, booking_date, booking_time, guests_count, 'новое', special_requests))
            
            booking_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"✅ Создано бронирование #{booking_id} на столик #{table_id}")
            return booking_id
            
        except Exception as e:
            print(f"❌ Ошибка бронирования столика: {e}")
            return None
    
    def get_table_info(self, table_id):
        """Получить информацию о столике"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT table_number, seats_count, location_type, description, status
                FROM tables 
                WHERE id = ? AND restaurant_id = 1
            """, (table_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'number': result[0],
                    'seats': result[1],
                    'location': result[2],
                    'description': result[3],
                    'status': result[4]
                }
            return None
            
        except Exception as e:
            print(f"❌ Ошибка получения информации о столике: {e}")
            return None
    
    def get_restaurant_tables_summary(self):
        """Получить сводку по всем столикам ресторана"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT location_type, COUNT(*), SUM(seats_count)
                FROM tables 
                WHERE restaurant_id = 1 AND status = 'active'
                GROUP BY location_type
            """)
            
            summary = cursor.fetchall()
            conn.close()
            
            result = {}
            for location, count, total_seats in summary:
                result[location] = {
                    'count': count,
                    'total_seats': total_seats
                }
            
            return result
            
        except Exception as e:
            print(f"❌ Ошибка получения сводки столиков: {e}")
            return {}
    
    def suggest_alternative_tables(self, date, time, guests_count, preferred_location=None):
        """Предложить альтернативные варианты столиков"""
        try:
            # Сначала пробуем точное совпадение
            exact_tables = self.get_available_tables(date, time, guests_count, preferred_location)
            
            if exact_tables:
                return {
                    'exact_match': exact_tables,
                    'alternatives': []
                }
            
            # Если точных совпадений нет, ищем альтернативы
            alternatives = []
            
            # 1. Столики с большим количеством мест
            bigger_tables = self.get_available_tables(date, time, guests_count + 2)
            if bigger_tables:
                alternatives.append({
                    'type': 'bigger',
                    'description': f'Столики на {guests_count + 2}+ мест',
                    'tables': bigger_tables[:3]  # Максимум 3 варианта
                })
            
            # 2. Другие типы расположения
            if preferred_location:
                other_locations = self.get_available_tables(date, time, guests_count)
                other_locations = [t for t in other_locations if t['location'] != preferred_location]
                if other_locations:
                    alternatives.append({
                        'type': 'different_location',
                        'description': 'Столики в других зонах',
                        'tables': other_locations[:3]
                    })
            
            return {
                'exact_match': [],
                'alternatives': alternatives
            }
            
        except Exception as e:
            print(f"❌ Ошибка поиска альтернатив: {e}")
            return {'exact_match': [], 'alternatives': []}

    # =============== ФУНКЦИИ CONFIDENCE SCORING ===============
    
    def analyze_response_confidence(self, user_text, ai_response, context_data=None):
        """
        Анализ уверенности в ответе ИИ
        Возвращает: словарь с confidence, should_escalate, reasons
        """
        confidence_score = 1.0
        should_escalate = False
        reasons = []
        
        # 1. Проверяем фразы неуверенности в ответе ИИ
        uncertainty_phrases = [
            'возможно', 'наверное', 'кажется', 'не уверен', 'может быть',
            'вероятно', 'думаю', 'предполагаю', 'не знаю точно'
        ]
        
        uncertainty_count = sum(1 for phrase in uncertainty_phrases 
                              if phrase in ai_response.lower())
        if uncertainty_count > 0:
            confidence_score -= min(0.4, uncertainty_count * 0.2)
            reasons.append(f"Неуверенные фразы: {uncertainty_count}")
        
        # 2. Проверяем наличие данных в ответе
        data_missing_phrases = [
            'не найден', 'нет информации', 'не могу найти', 
            'недоступно', 'отсутствует', 'не указано'
        ]
        
        if any(phrase in ai_response.lower() for phrase in data_missing_phrases):
            confidence_score -= 0.3
            reasons.append("Данные не найдены")
        
        # 3. Анализируем сложность запроса клиента
        complex_keywords = [
            'банкет', 'корпоратив', 'свадьба', 'день рождения',
            'особое меню', 'аллергия', 'диета', 'жалоба', 'проблема'
        ]
        
        if any(keyword in user_text.lower() for keyword in complex_keywords):
            confidence_score -= 0.2
            should_escalate = True
            reasons.append("Сложный запрос")
        
        # 4. Проверяем длину ответа (слишком короткие = подозрительные)
        if len(ai_response.split()) < 5:
            confidence_score -= 0.2
            reasons.append("Слишком короткий ответ")
        
        # 5. Финальная оценка эскалации
        if confidence_score < 0.6:
            should_escalate = True
            reasons.append("Низкий общий confidence")
        
        return {
            'confidence': max(0.0, confidence_score),
            'should_escalate': should_escalate,
            'reasons': reasons
        }
    
    def get_fallback_response(self, situation, confidence_analysis=None):
        """Получить fallback ответ для ситуации"""
        import random
        
        if situation in self.fallback_phrases:
            base_response = random.choice(self.fallback_phrases[situation])
            
            # Добавляем контекст если есть анализ
            if confidence_analysis and confidence_analysis['reasons']:
                reason = confidence_analysis['reasons'][0]
                if 'сложный' in reason.lower():
                    return "Ваш запрос требует особого внимания. Передаю нашему менеджеру."
            
            return base_response
        
        return "Минутку, уточняю информацию..."
    
    def should_request_human_help(self, user_text, conversation_history):
        """Определяет нужна ли помощь человека"""
        
        # Явные запросы на человека
        human_request_phrases = [
            'хочу говорить с человеком', 'соедините с менеджером',
            'позовите администратора', 'живой сотрудник',
            'не хочу с ботом', 'вы робот?'
        ]
        
        if any(phrase in user_text.lower() for phrase in human_request_phrases):
            return True, "Клиент запросил человека"
        
        # Повторяющиеся проблемы
        if len(conversation_history) >= 3:
            recent_messages = conversation_history[-3:]
            confusion_indicators = ['не понял', 'повторите', 'что?', 'как?']
            
            confusion_count = sum(1 for msg in recent_messages 
                                if any(indicator in msg.lower() for indicator in confusion_indicators))
            
            if confusion_count >= 2:
                return True, "Множественные недопонимания"
        
        return False, None
    
    def log_conversation_issue(self, user_id, user_text, ai_response, confidence_analysis, issue_type):
        """Логирование проблемных диалогов"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Создаем таблицу логов если её нет
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_issues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    user_text TEXT,
                    ai_response TEXT,
                    confidence_score REAL,
                    issue_type TEXT,
                    reasons TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved BOOLEAN DEFAULT FALSE
                )
            """)
            
            cursor.execute("""
                INSERT INTO conversation_issues 
                (user_id, user_text, ai_response, confidence_score, issue_type, reasons)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id, 
                user_text, 
                ai_response,
                confidence_analysis['confidence'],
                issue_type,
                ', '.join(confidence_analysis['reasons'])
            ))
            
            conn.commit()
            conn.close()
            
            print(f"🚨 Зафиксирована проблема: {issue_type} (confidence: {confidence_analysis['confidence']:.2f})")
            
        except Exception as e:
            print(f"❌ Ошибка логирования: {e}")

    # =============== СУЩЕСТВУЮЩИЕ ФУНКЦИИ БРОНИРОВАНИЙ ===============

    def get_user_bookings(self, user_phone):
        """Получить все бронирования пользователя по телефону"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT b.id, b.customer_name, b.booking_date, b.booking_time, b.guests_count, 
                       b.status, b.notes, b.created_at, b.table_id, t.table_number, t.location_type
                FROM bookings b
                LEFT JOIN tables t ON b.table_id = t.id
                WHERE b.customer_phone = ? 
                ORDER BY b.booking_date DESC, b.booking_time DESC
                LIMIT 10
            """, (user_phone,))
            
            bookings = cursor.fetchall()
            conn.close()
            
            result = []
            for booking in bookings:
                result.append({
                    'id': booking[0],
                    'name': booking[1], 
                    'date': booking[2],
                    'time': booking[3],
                    'guests': booking[4],
                    'status': booking[5],
                    'notes': booking[6],
                    'created': booking[7],
                    'table_id': booking[8],
                    'table_number': booking[9],
                    'table_location': booking[10]
                })
            
            return result
            
        except Exception as e:
            print(f"❌ Ошибка получения бронирований: {e}")
            return []
    
    def cancel_booking(self, booking_id, reason="Отменено по просьбе клиента"):
        """Отменить бронирование"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE bookings 
                SET status = 'отменено', notes = notes || ' | ОТМЕНА: ' || ?
                WHERE id = ?
            """, (reason, booking_id))
            
            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                return True
            else:
                conn.close()
                return False
                
        except Exception as e:
            print(f"❌ Ошибка отмены бронирования: {e}")
            return False
    
    def modify_booking(self, booking_id, new_date=None, new_time=None, new_guests=None):
        """Изменить бронирование"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            updates = []
            values = []
            
            if new_date:
                updates.append("booking_date = ?")
                values.append(new_date)
            
            if new_time:
                updates.append("booking_time = ?") 
                values.append(new_time)
                
            if new_guests:
                updates.append("guests_count = ?")
                values.append(new_guests)
            
            if updates:
                values.append(booking_id)
                query = f"UPDATE bookings SET {', '.join(updates)} WHERE id = ?"
                
                cursor.execute(query, values)
                
                if cursor.rowcount > 0:
                    conn.commit()
                    conn.close()
                    return True
            
            conn.close()
            return False
            
        except Exception as e:
            print(f"❌ Ошибка изменения бронирования: {e}")
            return False
    
    def check_availability(self, date, time):
        """Проверить доступность на дату и время"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM bookings 
                WHERE booking_date = ? AND booking_time = ? AND status != 'отменено'
            """, (date, time))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            # Предположим что у нас 10 столиков максимум
            return count < 10
            
        except Exception as e:
            print(f"❌ Ошибка проверки доступности: {e}")
            return True  # По умолчанию доступно
    
    def get_menu_by_category(self, category=None):
        """Получить меню по категории"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if category:
                cursor.execute("""
                    SELECT name, description, price FROM menu_items 
                    WHERE category = ? AND restaurant_id = 1
                    ORDER BY name
                """, (category,))
            else:
                cursor.execute("""
                    SELECT category, name, description, price FROM menu_items 
                    WHERE restaurant_id = 1
                    ORDER BY category, name
                """)
            
            items = cursor.fetchall()
            conn.close()
            
            return items
            
        except Exception as e:
            print(f"❌ Ошибка получения меню: {e}")
            return []

# Тестирование функций столиков
if __name__ == "__main__":
    tools = AITools()
    
    print("🧪 ТЕСТИРОВАНИЕ ФУНКЦИЙ СТОЛИКОВ:")
    print("=" * 50)
    
    # Тест 1: Поиск доступных столиков
    print("ТЕСТ 1: Поиск доступных столиков")
    available = tools.get_available_tables("2025-06-15", "19:00", 4)
    print(f"  Найдено столиков на 4 человека: {len(available)}")
    for table in available[:3]:
        print(f"    Столик #{table['number']}: {table['seats']} мест, {table['location']}")
    
    print()
    
    # Тест 2: Поиск по предпочтениям
    print("ТЕСТ 2: Поиск по предпочтениям")
    window_tables = tools.get_table_by_preference("2025-06-15", "19:00", 2, "хочу столик у окна")
    print(f"  Столики у окна: {len(window_tables)}")
    
    vip_tables = tools.get_table_by_preference("2025-06-15", "20:00", 6, "нужен VIP столик")
    print(f"  VIP столики: {len(vip_tables)}")
    
    print()
    
    # Тест 3: Сводка по столикам
    print("ТЕСТ 3: Сводка по столикам ресторана")
    summary = tools.get_restaurant_tables_summary()
    for location, info in summary.items():
        print(f"  {location}: {info['count']} столиков, {info['total_seats']} мест")
    
    print("\n✅ Тестирование функций столиков завершено!")