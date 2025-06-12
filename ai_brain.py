import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool
import asyncio

logger = logging.getLogger(__name__)

class AIBrain:
   """
   Настоящий AI-мозг системы с Function Calling
   ИИ принимает решения, извлекает данные, управляет диалогом
   """
   
   def __init__(self, gemini_key: str, db_path: str = 'restaurant.db'):
       self.db_path = db_path
       
       # Настройка Gemini с Function Calling
       genai.configure(api_key=gemini_key)
       
       # Создаем модель с tools
       self.model = genai.GenerativeModel(
           'gemini-1.5-flash',
           tools=[Tool(function_declarations=self._get_function_declarations())]
       )
       
       # Защита от Prompt Injection
       self.dangerous_patterns = [
           'ignore', 'forget', 'delete', 'system', 'admin', 'root',
           'drop table', 'truncate', 'bypass', 'override', 'disable'
       ]
       
       logger.info("🧠 AI-мозг инициализирован с Function Calling")
   
   def _get_function_declarations(self) -> List[FunctionDeclaration]:
       """Функции которые ИИ может вызывать"""
       return [
           FunctionDeclaration(
               name="search_tables",
               description="Найти доступные столики на дату и время",
               parameters={
                   "type": "object",
                   "properties": {
                       "date": {"type": "string", "description": "Дата YYYY-MM-DD"},
                       "time": {"type": "string", "description": "Время HH:MM"},
                       "guests": {"type": "integer", "description": "Количество гостей"},
                       "location": {"type": "string", "description": "Расположение: window, vip, quiet, stage, bar, center, terrace, banquet"}
                   },
                   "required": ["date", "time", "guests"]
               }
           ),
           FunctionDeclaration(
               name="create_booking",
               description="Создать новое бронирование",
               parameters={
                   "type": "object",
                   "properties": {
                       "name": {"type": "string", "description": "Имя клиента"},
                       "phone": {"type": "string", "description": "Телефон клиента"},
                       "date": {"type": "string", "description": "Дата YYYY-MM-DD"},
                       "time": {"type": "string", "description": "Время HH:MM"},
                       "guests": {"type": "integer", "description": "Количество гостей"},
                       "table_id": {"type": "integer", "description": "ID выбранного столика"},
                       "requests": {"type": "string", "description": "Особые пожелания"}
                   },
                   "required": ["name", "phone", "date", "time", "guests", "table_id"]
               }
           ),
           FunctionDeclaration(
               name="find_bookings",
               description="Найти бронирования клиента по телефону",
               parameters={
                   "type": "object",
                   "properties": {
                       "phone": {"type": "string", "description": "Телефон клиента"}
                   },
                   "required": ["phone"]
               }
           ),
           FunctionDeclaration(
               name="get_menu",
               description="Получить меню ресторана",
               parameters={
                   "type": "object",
                   "properties": {
                       "category": {"type": "string", "description": "Категория блюд (необязательно)"}
                   }
               }
           ),
           FunctionDeclaration(
               name="get_restaurant_info",
               description="Получить информацию о ресторане",
               parameters={
                   "type": "object",
                   "properties": {}
               }
           )
       ]
   
   def sanitize_input(self, text: str) -> str:
       """Защита от Prompt Injection"""
       text_lower = text.lower()
       
       for pattern in self.dangerous_patterns:
           if pattern in text_lower:
               logger.warning(f"🚨 Обнаружен опасный паттерн: {pattern}")
               return "Извините, не могу обработать этот запрос."
       
       if len(text) > 2000:
           logger.warning(f"🚨 Слишком длинный текст: {len(text)}")
           return text[:2000]
       
       return text
   
   async def process_message(self, user_id: int, user_text: str, conversation_history: List[str]) -> str:
       """
       ГЛАВНАЯ ФУНКЦИЯ: ИИ обрабатывает сообщение и принимает решения
       """
       try:
           # Защита от инъекций
           clean_text = self.sanitize_input(user_text)
           if clean_text != user_text:
               return clean_text
           
           # Формируем контекст для ИИ
           context = self._build_ai_context(user_id, user_text, conversation_history)
           
           # ИИ анализирует и принимает решения
           response = await self._call_ai_with_functions(context)
           
           # Логируем действие ИИ
           self._log_ai_decision(user_id, user_text, response)
           
           return response
           
       except Exception as e:
           logger.error(f"❌ Ошибка обработки сообщения: {e}")
           return "Извините, произошла техническая ошибка. Попробуйте еще раз."
   
   def _build_ai_context(self, user_id: int, user_text: str, history: List[str]) -> str:
       """Формируем контекст для ИИ"""
       
       # Получаем информацию о ресторане
       restaurant_info = self._get_restaurant_context()
       
       # Последние сообщения
       recent_history = "\n".join(history[-5:]) if history else "Первое сообщение"
       
       context = f"""
Ты умный голосовой помощник ресторана. Ты ДОЛЖЕН использовать доступные функции для реальных действий.

ИНФОРМАЦИЯ О РЕСТОРАНЕ:
{restaurant_info}

ИСТОРИЯ ДИАЛОГА:
{recent_history}

НОВОЕ СООБЩЕНИЕ КЛИЕНТА: {user_text}

ИНСТРУКЦИИ:
1. Анализируй что хочет клиент
2. Если нужно найти столики - вызови search_tables
3. Если нужно забронировать - вызови create_booking  
4. Если спрашивает про свои бронирования - вызови find_bookings
5. Если про меню - вызови get_menu
6. ВСЕГДА используй функции для реальных действий, не выдумывай данные
7. Отвечай кратко и по делу
8. Будь вежливым и профессиональным

Что будешь делать?
"""
       return context
   
   def _get_restaurant_context(self) -> str:
       """Получаем информацию о ресторане для контекста"""
       try:
           conn = sqlite3.connect(self.db_path)
           cursor = conn.cursor()
           
           cursor.execute("SELECT name, phone, address, working_hours FROM restaurants WHERE id = 1")
           restaurant = cursor.fetchone()
           
           conn.close()
           
           if restaurant:
               return f"Ресторан: {restaurant[0]}, Телефон: {restaurant[1]}, Адрес: {restaurant[2]}, Часы работы: {restaurant[3]}"
           else:
               return "Информация о ресторане недоступна"
               
       except Exception as e:
           logger.error(f"❌ Ошибка получения контекста ресторана: {e}")
           return "Ошибка загрузки информации о ресторане"
   
   async def _call_ai_with_functions(self, context: str) -> str:
       """Вызов ИИ с возможностью использования функций"""
       try:
           # Отправляем запрос к ИИ
           response = await asyncio.to_thread(self.model.generate_content, context)
           
           # Проверяем использовал ли ИИ функции
           if response.candidates[0].content.parts:
               for part in response.candidates[0].content.parts:
                   if hasattr(part, 'function_call') and part.function_call:
                       # ИИ вызвал функцию - выполняем её
                       function_result = await self._execute_function(part.function_call)
                       
                       # Отправляем результат функции обратно ИИ
                       follow_up = await asyncio.to_thread(self.model.generate_content, [
                           context,
                           response,
                           genai.types.FunctionResponse(
                               name=part.function_call.name,
                               response=function_result
                           )
                       ])
                       
                       return follow_up.text
           
           # ИИ ответил без функций
           return response.text
           
       except Exception as e:
           logger.error(f"❌ Ошибка вызова ИИ: {e}")
           return "Извините, не могу обработать ваш запрос в данный момент."
   
   async def _execute_function(self, function_call) -> Dict:
       """Выполнение функции которую вызвал ИИ"""
       function_name = function_call.name
       args = dict(function_call.args)
       
       logger.info(f"🤖 ИИ вызывает функцию: {function_name} с параметрами: {args}")
       
       try:
           if function_name == "search_tables":
               return self._search_tables(**args)
           elif function_name == "create_booking":
               return self._create_booking(**args)
           elif function_name == "find_bookings":
               return self._find_bookings(**args)
           elif function_name == "get_menu":
               return self._get_menu(**args)
           elif function_name == "get_restaurant_info":
               return self._get_restaurant_info()
           else:
               return {"error": f"Неизвестная функция: {function_name}"}
               
       except Exception as e:
           logger.error(f"❌ Ошибка выполнения функции {function_name}: {e}")
           return {"error": f"Ошибка выполнения функции: {str(e)}"}
   
   def _log_ai_decision(self, user_id: int, user_text: str, ai_response: str):
       """Логирование решений ИИ"""
       try:
           conn = sqlite3.connect(self.db_path)
           cursor = conn.cursor()
           
           cursor.execute("""
               CREATE TABLE IF NOT EXISTS ai_decisions_log (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   user_id INTEGER,
                   user_message TEXT,
                   ai_response TEXT,
                   timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
               )
           """)
           
           cursor.execute("""
               INSERT INTO ai_decisions_log (user_id, user_message, ai_response)
               VALUES (?, ?, ?)
           """, (user_id, user_text, ai_response))
           
           conn.commit()
           conn.close()
           
       except Exception as e:
           logger.error(f"❌ Ошибка логирования: {e}")
   
   # ========== ФУНКЦИИ БАЗЫ ДАННЫХ ==========
   
   def _search_tables(self, date: str, time: str, guests: int, location: str = None) -> Dict:
       """Поиск доступных столиков"""
       try:
           conn = sqlite3.connect(self.db_path)
           cursor = conn.cursor()
           
           # Базовый запрос
           query = """
               SELECT t.id, t.table_number, t.seats_count, t.location_type, t.description
               FROM tables t
               WHERE t.restaurant_id = 1 
               AND t.status = 'active'
               AND t.seats_count >= ?
           """
           params = [guests]
           
           # Фильтр по расположению
           if location:
               query += " AND t.location_type = ?"
               params.append(location)
           
           cursor.execute(query, params)
           all_tables = cursor.fetchall()
           
           # Проверяем занятость
           cursor.execute("""
               SELECT DISTINCT table_id 
               FROM bookings 
               WHERE booking_date = ? 
               AND booking_time = ? 
               AND status != 'отменено'
               AND table_id IS NOT NULL
           """, (date, time))
           
           occupied_ids = [row[0] for row in cursor.fetchall()]
           conn.close()
           
           # Свободные столики
           available = []
           for table in all_tables:
               table_id, number, seats, loc, desc = table
               if table_id not in occupied_ids:
                   available.append({
                       'id': table_id,
                       'number': number,
                       'seats': seats,
                       'location': loc,
                       'description': desc
                   })
           
           return {
               "success": True,
               "tables": available,
               "count": len(available)
           }
           
       except Exception as e:
           logger.error(f"❌ Ошибка поиска столиков: {e}")
           return {"success": False, "error": str(e)}
   
   def _create_booking(self, name: str, phone: str, date: str, time: str, guests: int, table_id: int, requests: str = "") -> Dict:
       """Создание бронирования"""
       try:
           conn = sqlite3.connect(self.db_path)
           cursor = conn.cursor()
           
           # Проверяем свободен ли столик
           cursor.execute("""
               SELECT COUNT(*) FROM bookings 
               WHERE table_id = ? 
               AND booking_date = ? 
               AND booking_time = ? 
               AND status != 'отменено'
           """, (table_id, date, time))
           
           if cursor.fetchone()[0] > 0:
               conn.close()
               return {"success": False, "error": "Столик уже занят на это время"}
           
           # Создаем бронирование
           cursor.execute("""
               INSERT INTO bookings 
               (restaurant_id, table_id, customer_name, customer_phone, booking_date, booking_time, guests_count, status, special_requests)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           """, (1, table_id, name, phone, date, time, guests, 'новое', requests))
           
           booking_id = cursor.lastrowid
           
           # Получаем инфо о столике
           cursor.execute("""
               SELECT table_number, location_type, description
               FROM tables WHERE id = ?
           """, (table_id,))
           
           table_info = cursor.fetchone()
           conn.commit()
           conn.close()
           
           return {
               "success": True,
               "booking_id": booking_id,
               "table_number": table_info[0],
               "table_location": table_info[1],
               "table_description": table_info[2]
           }
           
       except Exception as e:
           logger.error(f"❌ Ошибка создания бронирования: {e}")
           return {"success": False, "error": str(e)}
   
   def _find_bookings(self, phone: str) -> Dict:
       """Поиск бронирований клиента"""
       try:
           conn = sqlite3.connect(self.db_path)
           cursor = conn.cursor()
           
           cursor.execute("""
               SELECT b.id, b.customer_name, b.booking_date, b.booking_time, 
                      b.guests_count, b.status, b.special_requests, 
                      t.table_number, t.location_type
               FROM bookings b
               LEFT JOIN tables t ON b.table_id = t.id
               WHERE b.customer_phone = ? 
               ORDER BY b.booking_date DESC, b.booking_time DESC
               LIMIT 10
           """, (phone,))
           
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
                   'requests': booking[6],
                   'table_number': booking[7],
                   'table_location': booking[8]
               })
           
           return {
               "success": True,
               "bookings": result,
               "count": len(result)
           }
           
       except Exception as e:
           logger.error(f"❌ Ошибка поиска бронирований: {e}")
           return {"success": False, "error": str(e)}
   
   def _get_menu(self, category: str = None) -> Dict:
       """Получение меню"""
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
           
           menu_data = []
           for item in items:
               if category:
                   menu_data.append({
                       'name': item[0],
                       'description': item[1],
                       'price': item[2]
                   })
               else:
                   menu_data.append({
                       'category': item[0],
                       'name': item[1],
                       'description': item[2],
                       'price': item[3]
                   })
           
           return {
               "success": True,
               "menu": menu_data,
               "count": len(menu_data)
           }
           
       except Exception as e:
           logger.error(f"❌ Ошибка получения меню: {e}")
           return {"success": False, "error": str(e)}
   
   def _get_restaurant_info(self) -> Dict:
       """Информация о ресторане"""
       try:
           conn = sqlite3.connect(self.db_path)
           cursor = conn.cursor()
           
           cursor.execute("""
               SELECT name, phone, address, working_hours, greeting_message, ai_personality
               FROM restaurants WHERE id = 1
           """)
           
           restaurant = cursor.fetchone()
           conn.close()
           
           if restaurant:
               return {
                   "success": True,
                   "name": restaurant[0],
                   "phone": restaurant[1],
                   "address": restaurant[2],
                   "hours": restaurant[3],
                   "greeting": restaurant[4],
                   "personality": restaurant[5]
               }
           else:
               return {"success": False, "error": "Ресторан не найден"}
               
       except Exception as e:
           logger.error(f"❌ Ошибка получения информации о ресторане: {e}")
           return {"success": False, "error": str(e)}
   
   def save_conversation(self, user_id: int, user_name: str, message_text: str, bot_response: str):
       """Сохранение диалога"""
       try:
           conn = sqlite3.connect(self.db_path)
           cursor = conn.cursor()
           
           cursor.execute("""
               INSERT INTO conversations (user_id, user_name, message_text, bot_response)
               VALUES (?, ?, ?, ?)
           """, (user_id, user_name, message_text, bot_response))
           
           conn.commit()
           conn.close()
           
       except Exception as e:
           logger.error(f"❌ Ошибка сохранения диалога: {e}")
   
   def get_conversation_history(self, user_id: int, limit: int = 10) -> List[str]:
       """Получение истории диалогов"""
       try:
           conn = sqlite3.connect(self.db_path)
           cursor = conn.cursor()
           
           cursor.execute("""
               SELECT message_text, bot_response FROM conversations 
               WHERE user_id = ? 
               ORDER BY timestamp DESC 
               LIMIT ?
           """, (user_id, limit))
           
           history = cursor.fetchall()
           conn.close()
           
           # Формируем список диалогов
           result = []
           for message, response in reversed(history):
               result.append(f"Клиент: {message}")
               result.append(f"Бот: {response}")
           
           return result
           
       except Exception as e:
           logger.error(f"❌ Ошибка получения истории: {e}")
           return []