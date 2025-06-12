# Супер-умный голосовой бот с полной интеграцией AI + Confidence Scoring + Столики
# Версия с интеграцией системы столиков

import asyncio
import logging
import tempfile
import os
import sqlite3
import re
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
import speech_recognition as sr
from pydub import AudioSegment
from gtts import gTTS
import google.generativeai as genai
from ai_tools import AITools

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SuperSmartVoiceBot:
    """Супер-умный голосовой бот с confidence scoring, fallback логикой и системой столиков"""
    
    def __init__(self, telegram_token, gemini_key):
        self.telegram_token = telegram_token
        self.gemini_key = gemini_key
        
        # Настройка Gemini
        genai.configure(api_key=self.gemini_key)
        
        try:
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            print("🧠 Используем модель: gemini-1.5-flash")
        except:
            try:
                self.model = genai.GenerativeModel('gemini-1.5-pro')
                print("🧠 Используем модель: gemini-1.5-pro")
            except:
                print("❌ Не удалось подключить Gemini")
                self.model = None
        
        self.recognizer = sr.Recognizer()
        self.ai_tools = AITools()  # Подключаем обновленные AI инструменты
        
        print("🤖 Супер-умный голосовой бот создан!")
        print("🛡️ Confidence scoring активирован")
        print("🔄 Fallback логика подключена")
        print("🪑 Система столиков интегрирована")
        print("🎤 Готов к распознаванию речи")
    
    def save_conversation(self, user_id, user_name, message_text, bot_response):
        """Сохранение диалога в базу данных"""
        try:
            conn = sqlite3.connect('restaurant.db')
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO conversations (user_id, user_name, message_text, bot_response)
                VALUES (?, ?, ?, ?)
            """, (user_id, user_name, message_text, bot_response))
            
            conn.commit()
            conn.close()
            
            print(f"💾 Диалог сохранен для пользователя {user_name}")
            
        except Exception as e:
            print(f"❌ Ошибка сохранения диалога: {e}")
    
    def get_conversation_history(self, user_id, limit=10):
        """Получение истории диалогов пользователя"""
        try:
            conn = sqlite3.connect('restaurant.db')
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT message_text, bot_response, timestamp 
                FROM conversations 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (user_id, limit))
            
            history = cursor.fetchall()
            conn.close()
            
            return list(reversed(history))
            
        except Exception as e:
            print(f"❌ Ошибка получения истории: {e}")
            return []
    
    def extract_table_preferences(self, user_text):
        """Извлечение предпочтений по столикам из текста клиента"""
        preferences = {
            'location': None,
            'special_requests': []
        }
        
        text_lower = user_text.lower()
        
        # Определяем предпочтения по расположению
        location_mapping = {
            'окн': 'window',
            'вид': 'window',
            'панорам': 'window',
            'сцен': 'stage', 
            'музык': 'stage',
            'живая музыка': 'stage',
            'тих': 'quiet',
            'спокой': 'quiet',
            'без шума': 'quiet',
            'vip': 'vip',
            'вип': 'vip',
            'особ': 'vip',
            'важ': 'vip',
            'бар': 'bar',
            'барн': 'bar',
            'стойк': 'bar',
            'террас': 'terrace',
            'летн': 'terrace',
            'открыт': 'terrace',
            'банкет': 'banquet',
            'больш': 'banquet',
            'компани': 'banquet'
        }
        
        for keyword, location in location_mapping.items():
            if keyword in text_lower:
                preferences['location'] = location
                print(f"🔍 Обнаружено предпочтение: {keyword} → {location}")
                break
        
        # Извлекаем особые пожелания
        special_requests = []
        if 'день рождения' in text_lower:
            special_requests.append('День рождения')
        if 'годовщина' in text_lower:
            special_requests.append('Годовщина')
        if 'романтик' in text_lower:
            special_requests.append('Романтический ужин')
        if 'деловая встреча' in text_lower or 'бизнес' in text_lower:
            special_requests.append('Деловая встреча')
        
        preferences['special_requests'] = special_requests
        
        return preferences
    
    def get_ai_context_with_data(self, user_id, user_text):
        """Формирование расширенного контекста с данными из базы + информация о столиках"""
        
        # Получаем историю диалогов
        history = self.get_conversation_history(user_id, limit=50)
        
        # Пытаемся найти телефон пользователя из истории
        user_phone = None
        for message, response, timestamp in history:
            phone_match = re.search(r'\+?\d[\d\s\-\(\)]{9,}', message)
            if phone_match:
                user_phone = re.sub(r'[\s\-\(\)]', '', phone_match.group(0))
                break
        
        context = f"Новое сообщение клиента: {user_text}\n\n"
        
        # Добавляем историю диалога (только последние 3 для краткости)
        if history:
            context += "Краткая история диалога:\n"
            for message, response, timestamp in history[-3:]:
                context += f"Клиент: {message}\nБот: {response}\n\n"
        
        # Добавляем данные из базы если есть телефон
        context_data = {}
        if user_phone:
            print(f"🔍 Ищу бронирования для телефона: {user_phone}")
            bookings = self.ai_tools.get_user_bookings(user_phone)
            print(f"🔍 Найдено бронирований: {len(bookings)}")
            
            context_data['bookings'] = bookings
            
            if bookings:
                context += f"КРИТИЧЕСКИ ВАЖНАЯ ИНФОРМАЦИЯ - У КЛИЕНТА ЕСТЬ БРОНИРОВАНИЯ:\n"
                context += f"Телефон клиента: {user_phone}\n"
                for booking in bookings:
                    table_info = ""
                    if booking.get('table_number'):
                        table_info = f" на столик #{booking['table_number']}"
                        if booking.get('table_location'):
                            table_info += f" ({booking['table_location']})"
                    
                    context += f"Бронирование №{booking['id']}: дата {booking['date']}, время {booking['time']}, гостей {booking['guests']}, статус '{booking['status']}'{table_info}\n"
                context += "\n"
            else:
                context += f"У клиента нет активных бронирований (телефон {user_phone})\n\n"
        else:
            print("🔍 Телефон пользователя не найден в истории диалогов")
            context += "Телефон клиента неизвестен\n\n"
        
        # НОВОЕ: Добавляем информацию о доступных столиках если клиент спрашивает о бронировании
        if any(word in user_text.lower() for word in ['бронир', 'столик', 'место', 'забронировать']):
            table_summary = self.ai_tools.get_restaurant_tables_summary()
            if table_summary:
                context += "ДОСТУПНЫЕ ТИПЫ СТОЛИКОВ В РЕСТОРАНЕ:\n"
                for location, info in table_summary.items():
                    location_name = {
                        'window': 'у окна',
                        'vip': 'VIP зона', 
                        'stage': 'у сцены',
                        'quiet': 'тихая зона',
                        'bar': 'у бара',
                        'center': 'центр зала',
                        'terrace': 'терраса',
                        'banquet': 'банкетный зал'
                    }.get(location, location)
                    
                    context += f"- {location_name}: {info['count']} столиков, всего {info['total_seats']} мест\n"
                context += "\n"
        
        return context, context_data
    
    def create_booking_with_table(self, customer_name, customer_phone, booking_date, booking_time, guests_count, user_text, notes=""):
        """Создание бронирования с учетом предпочтений по столикам"""
        try:
            print(f"🪑 Создаю бронирование с учетом столиков для {customer_name}")
            
            # Извлекаем предпочтения из текста клиента
            preferences = self.extract_table_preferences(user_text)
            print(f"🔍 Предпочтения клиента: {preferences}")
            
            # Ищем подходящие столики
            if preferences['location']:
                available_tables = self.ai_tools.get_table_by_preference(
                    booking_date, booking_time, guests_count, user_text
                )
            else:
                available_tables = self.ai_tools.get_available_tables(
                    booking_date, booking_time, guests_count
                )
            
            print(f"🔍 Найдено подходящих столиков: {len(available_tables)}")
            
            if available_tables:
                # Выбираем лучший столик (первый из подходящих)
                best_table = available_tables[0]
                print(f"✅ Выбран столик #{best_table['number']} ({best_table['location']}, {best_table['seats']} мест)")
                
                # Формируем заметки с особыми пожеланиями
                special_notes = notes
                if preferences['special_requests']:
                    special_notes += f" | Особые пожелания: {', '.join(preferences['special_requests'])}"
                
                # Создаем бронирование на конкретный столик
                booking_id = self.ai_tools.book_specific_table(
                    table_id=best_table['id'],
                    customer_name=customer_name,
                    customer_phone=customer_phone,
                    booking_date=booking_date,
                    booking_time=booking_time,
                    guests_count=guests_count,
                    special_requests=special_notes
                )
                
                if booking_id:
                    # Формируем красивый ответ
                    location_names = {
                        'window': 'у окна с прекрасным видом',
                        'vip': 'в VIP зоне',
                        'stage': 'у сцены с живой музыкой',
                        'quiet': 'в тихой зоне',
                        'bar': 'у барной стойки',
                        'center': 'в центре зала',
                        'terrace': 'на летней террасе',
                        'banquet': 'в банкетном зале'
                    }
                    
                    location_desc = location_names.get(best_table['location'], best_table['location'])
                    
                    response = f"🎉 Отлично! Ваше бронирование подтверждено!\n\n"
                    response += f"📋 Номер бронирования: #{booking_id}\n"
                    response += f"👤 Имя: {customer_name}\n"
                    response += f"📞 Телефон: {customer_phone}\n"
                    response += f"📅 Дата: {booking_date}\n"
                    response += f"🕒 Время: {booking_time}\n"
                    response += f"👥 Гостей: {guests_count}\n"
                    response += f"🪑 Столик: #{best_table['number']} {location_desc} ({best_table['seats']} мест)\n"
                    
                    if best_table['description']:
                        response += f"✨ Особенности: {best_table['description']}\n"
                    
                    if preferences['special_requests']:
                        response += f"🎯 Особые пожелания: {', '.join(preferences['special_requests'])}\n"
                    
                    response += f"\n✅ Ждем вас в ресторане!"
                    
                    return response
                
            else:
                # Если подходящих столиков нет - предлагаем альтернативы
                alternatives = self.ai_tools.suggest_alternative_tables(booking_date, booking_time, guests_count, preferences['location'])
                
                if alternatives['alternatives']:
                    response = f"😔 К сожалению, столики "
                    if preferences['location']:
                        location_names = {
                            'window': 'у окна',
                            'vip': 'VIP',
                            'stage': 'у сцены',
                            'quiet': 'в тихой зоне',
                            'bar': 'у бара',
                            'center': 'в центре',
                            'terrace': 'на террасе',
                            'banquet': 'банкетные'
                        }
                        response += location_names.get(preferences['location'], preferences['location'])
                    
                    response += f" на {booking_date} в {booking_time} заняты.\n\n"
                    response += "Но у нас есть отличные альтернативы:\n\n"
                    
                    for alt in alternatives['alternatives']:
                        response += f"📍 {alt['description']}:\n"
                        for table in alt['tables']:
                            response += f"• Столик #{table['number']} ({table['seats']} мест) - {table['description']}\n"
                        response += "\n"
                    
                    response += "Какой вариант вам подходит?"
                    return response
                else:
                    return f"😔 К сожалению, все столики на {booking_date} в {booking_time} заняты. Предложить другое время?"
            
            return "❌ Произошла ошибка при создании бронирования. Попробуйте еще раз."
            
        except Exception as e:
            print(f"❌ Ошибка создания бронирования со столиками: {e}")
            return "❌ Ошибка создания бронирования. Попробуйте еще раз."
    
    def get_booking_in_progress(self, user_id):
        """Получить данные бронирования из истории диалогов"""
        try:
            conn = sqlite3.connect('restaurant.db')
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT message_text FROM conversations 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 50
            """, (user_id,))
            
            messages = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            booking_data = {}
            
            for msg in messages:
                # Ищем имя
                name_match = re.search(r'меня зовут\s+(\w+)|на имя\s+(\w+)|зовут\s+(\w+)', msg, re.IGNORECASE)
                if name_match and 'name' not in booking_data:
                    name = (name_match.group(1) or name_match.group(2) or name_match.group(3)).capitalize()
                    booking_data['name'] = name
                
                # Ищем телефон
                phone_match = re.search(r'\+?\d[\d\s\-\(\)]{9,}', msg)
                if phone_match and 'phone' not in booking_data:
                    phone = re.sub(r'[\s\-\(\)]', '', phone_match.group(0))
                    booking_data['phone'] = phone
                
                # Ищем количество гостей
                if any(word in msg.lower() for word in ['бронир', 'столик', 'новое', 'еще']):
                    guests_match = re.search(r'(\d+)\s*чел|(\d+)\s*человек|(\d+)\s*персон|(\d+)\s*гост', msg, re.IGNORECASE)
                    if guests_match and 'guests' not in booking_data:
                        guests_str = guests_match.group(1) or guests_match.group(2) or guests_match.group(3) or guests_match.group(4)
                        guests = int(guests_str)
                        if 1 <= guests <= 20:
                            booking_data['guests'] = guests
                
                # Ищем дату и время
                if any(word in msg.lower() for word in ['бронир', 'столик', 'новое', 'еще']) and 'date' not in booking_data:
                    today = datetime.now()
                    if 'завтра' in msg.lower() and 'после' not in msg.lower():
                        booking_data['date'] = (today + timedelta(days=1)).strftime('%Y-%m-%d')
                    elif 'послезавтра' in msg.lower():
                        booking_data['date'] = (today + timedelta(days=2)).strftime('%Y-%m-%d')
                
                if any(word in msg.lower() for word in ['бронир', 'столик', 'новое', 'еще']):
                    time_match = re.search(r'(\d{1,2}):(\d{2})|в\s+(\d{1,2})|на\s+(\d{1,2})\s*час', msg, re.IGNORECASE)
                    if time_match and 'time' not in booking_data:
                        if time_match.group(1) and time_match.group(2):
                            booking_data['time'] = f"{int(time_match.group(1)):02d}:{time_match.group(2)}"
                        else:
                            hour_str = time_match.group(3) or time_match.group(4)
                            hour = int(hour_str)
                            if 10 <= hour <= 23:
                                booking_data['time'] = f"{hour:02d}:00"
            
            return booking_data
            
        except Exception as e:
            print(f"❌ Ошибка получения данных бронирования: {e}")
            return {}
    
    def should_create_new_booking(self, user_text, user_id):
        """Проверяет нужно ли создавать НОВОЕ бронирование"""
        
        new_booking_keywords = [
            'новое бронирование', 'еще одно', 'дополнительное', 
            'второе бронирование', 'другое бронирование',
            'хочу забронировать еще', 'нужно еще'
        ]
        
        text_lower = user_text.lower()
        wants_new = any(keyword in text_lower for keyword in new_booking_keywords)
        
        history = self.get_conversation_history(user_id, limit=10)
        
        recent_bookings = 0
        for message, response, timestamp in history:
            if 'бронирование создано' in response.lower() or 'номер бронирования' in response.lower() or 'бронирование подтверждено' in response.lower():
                recent_bookings += 1
        
        if recent_bookings > 0:
            return wants_new
        
        return 'бронир' in text_lower or 'столик' in text_lower
    
    def check_and_create_booking_with_tables(self, text, user_name, user_id):
        """Умная проверка и создание бронирования С УЧЕТОМ СТОЛИКОВ"""
        
        if not self.should_create_new_booking(text, user_id):
            return None
        
        booking_data = self.get_booking_in_progress(user_id)
        
        required_fields = ['name', 'phone', 'guests']
        missing = [field for field in required_fields if field not in booking_data]
        
        if not missing:
            if 'date' not in booking_data:
                booking_data['date'] = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            
            if 'time' not in booking_data:
                booking_data['time'] = "19:00"
            
            # НОВОЕ: Создаем бронирование с учетом столиков
            return self.create_booking_with_table(
                customer_name=booking_data['name'],
                customer_phone=booking_data['phone'],
                booking_date=booking_data['date'],
                booking_time=booking_data['time'],
                guests_count=booking_data['guests'],
                user_text=text,  # Передаем оригинальный текст для анализа предпочтений
                notes=f"Создано через умный диалог с ботом пользователем {user_name}"
            )
        
        return None
    
    def get_restaurant_info(self):
        """Получение информации о ресторане из базы"""
        try:
            conn = sqlite3.connect('restaurant.db')
            cursor = conn.cursor()
            
            cursor.execute("SELECT name, phone, address, working_hours, greeting_message FROM restaurants WHERE id = 1")
            restaurant_data = cursor.fetchone()
            
            cursor.execute("SELECT category, name, description, price FROM menu_items WHERE restaurant_id = 1 LIMIT 5")
            menu_items = cursor.fetchall()
            
            conn.close()
            
            if restaurant_data:
                name, phone, address, working_hours, greeting = restaurant_data
                
                menu_text = ""
                if menu_items:
                    menu_text = "\n\nПопулярные блюда:\n"
                    for category, item_name, description, price in menu_items:
                        menu_text += f"• {item_name} - {price}₽\n"
                
                return {
                    'name': name,
                    'phone': phone, 
                    'address': address,
                    'working_hours': working_hours,
                    'greeting': greeting,
                    'menu': menu_text
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Ошибка получения данных ресторана: {e}")
            return None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        
        ai_status = "🧠 ИИ подключен" if self.model else "⚠️ ИИ недоступен"
        
        restaurant = self.get_restaurant_info()
        if restaurant and restaurant['greeting']:
            greeting = restaurant['greeting']
        else:
            greeting = "Добро пожаловать в наш ресторан!"
        
        welcome_message = f"""
🎙️ {greeting}

Что я умею:
🎤 Понимаю голосовые сообщения
🔊 Отвечаю голосом  
📊 Работаю с базой данных ресторана
🪑 Умная система столиков (у окна, VIP, тихие зоны)
📅 Управляю бронированиями (создание, отмена, изменение)
🍽️ Расскажу о меню и ценах
🧠 Помню все наши разговоры
🛡️ Умная система confidence scoring
🔄 Fallback логика при проблемах
{ai_status}

Попробуйте сказать: "Хочу столик у окна на завтра на 4 человека"
        """
        
        await update.message.reply_text(welcome_message)
        self.save_conversation(user_id, user_name, "/start", welcome_message)
        print(f"✅ Пользователь {user_name} (ID: {user_id}) запустил бота с системой столиков")
    
    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка голосовых сообщений с confidence checking"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        
        try:
            print(f"🎤 Получено голосовое сообщение от {user_name} (ID: {user_id})")
            
            await update.message.reply_text("🎤 Слушаю ваше сообщение...")
            
            voice_file = await update.message.voice.get_file()
            voice_data = await voice_file.download_as_bytearray()
            
            user_text = await self.speech_to_text(voice_data)
            
            if not user_text:
                fallback_response = self.ai_tools.get_fallback_response('error')
                await update.message.reply_text(fallback_response)
                return
            
            print(f"📝 Распознанный текст: {user_text}")
            await update.message.reply_text(f"✅ Вы сказали: '{user_text}'\n\n🤔 Ищу подходящие столики...")
            
            bot_response = await self.process_message_with_confidence(user_id, user_name, user_text)
            
            await update.message.reply_text(bot_response)
            
            voice_response = await self.text_to_speech(bot_response)
            if voice_response:
                await update.message.reply_voice(voice=voice_response)
            
            self.save_conversation(user_id, user_name, user_text, bot_response)
                
        except Exception as e:
            print(f"❌ Ошибка обработки голоса: {e}")
            fallback_response = self.ai_tools.get_fallback_response('error')
            await update.message.reply_text(fallback_response)
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений с confidence checking"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        user_text = update.message.text
        
        print(f"💬 Текстовое сообщение от {user_name} (ID: {user_id}): {user_text}")
        
        await update.message.reply_text("🤔 Анализирую сообщение и ищу подходящие столики...")
        
        bot_response = await self.process_message_with_confidence(user_id, user_name, user_text)
        
        await update.message.reply_text(bot_response)
        
        voice_response = await self.text_to_speech(bot_response)
        if voice_response:
            await update.message.reply_voice(voice=voice_response)
        
        self.save_conversation(user_id, user_name, user_text, bot_response)
    
    async def process_message_with_confidence(self, user_id, user_name, user_text):
        """ОБНОВЛЕННАЯ ФУНКЦИЯ: Обработка сообщения с confidence checking + столики"""
        
        # 1. Проверяем нужна ли помощь человека
        conversation_history = self.get_conversation_history(user_id)
        needs_human, reason = self.ai_tools.should_request_human_help(user_text, [msg[0] for msg in conversation_history])
        
        if needs_human:
            print(f"🚨 Требуется помощь человека: {reason}")
            return self.ai_tools.get_fallback_response('complex_request')
        
        # 2. НОВОЕ: Проверяем создание бронирования С УЧЕТОМ СТОЛИКОВ
        booking_response = self.check_and_create_booking_with_tables(user_text, user_name, user_id)
        if booking_response:
            return booking_response
        
        # 3. Получаем ответ от ИИ с учетом столиков
        context, context_data = self.get_ai_context_with_data(user_id, user_text)
        
        if self.model:
            ai_response = await self.get_ai_response(context, user_id)
        else:
            ai_response = self.get_simple_response(user_text, user_name)
        
        # 4. АНАЛИЗИРУЕМ CONFIDENCE ОТВЕТА ИИ
        if ai_response:
            confidence_analysis = self.ai_tools.analyze_response_confidence(
                user_text, ai_response, context_data
            )
            
            print(f"🔍 Confidence: {confidence_analysis['confidence']:.2f}")
            print(f"🔍 Эскалация: {confidence_analysis['should_escalate']}")
            print(f"🔍 Причины: {confidence_analysis['reasons']}")
            
            # 5. ПРИНИМАЕМ РЕШЕНИЕ НА ОСНОВЕ CONFIDENCE
            if confidence_analysis['should_escalate']:
                # Логируем проблему
                self.ai_tools.log_conversation_issue(
                    user_id, user_text, ai_response, confidence_analysis, "low_confidence"
                )
                
                # Возвращаем fallback ответ
                if confidence_analysis['confidence'] < 0.4:
                    return self.ai_tools.get_fallback_response('complex_request', confidence_analysis)
                else:
                    return self.ai_tools.get_fallback_response('low_confidence', confidence_analysis)
            
            # 6. Если confidence нормальный - возвращаем ответ ИИ
            return ai_response
        
        # 7. Если ИИ вообще не ответил
        return self.ai_tools.get_fallback_response('error')
    
    async def speech_to_text(self, audio_data):
        """Конвертация голоса в текст"""
        try:
            print("🔄 Конвертирую голос в текст...")
            
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            audio = AudioSegment.from_ogg(temp_file_path)
            wav_path = temp_file_path.replace('.ogg', '.wav')
            audio.export(wav_path, format="wav")
            
            with sr.AudioFile(wav_path) as source:
                audio_data = self.recognizer.record(source)
            
            try:
                text = self.recognizer.recognize_google(audio_data, language='ru-RU')
                print("🇷🇺 Распознано на русском")
            except sr.UnknownValueError:
                try:
                    text = self.recognizer.recognize_google(audio_data, language='az-AZ')
                    print("🇦🇿 Распознано на азербайджанском")
                except sr.UnknownValueError:
                    text = None
            
            os.unlink(temp_file_path)
            os.unlink(wav_path)
            
            return text
            
        except Exception as e:
            print(f"❌ Ошибка распознавания речи: {e}")
            return None
    
    async def get_ai_response(self, context, user_id):
        """Получение ответа от Gemini AI с учетом контекста, базы данных И столиков"""
        try:
            print("🧠 Запрашиваю умный ответ у ИИ с учетом столиков...")
            
            restaurant = self.get_restaurant_info()
            
            if restaurant:
                restaurant_info = f"""
Информация о ресторане:
- Название: {restaurant['name']}
- Адрес: {restaurant['address']}
- Телефон: {restaurant['phone']}
- Часы работы: {restaurant['working_hours']}
"""
            else:
                restaurant_info = "Информация о ресторане временно недоступна."
            
            prompt = f"""
Ты администратор ресторана. Отвечай кратко и конкретно.

{restaurant_info}

ВАЖНО: В контексте ниже есть ВСЯ информация о клиенте И доступных столиках.

Если в контексте указаны бронирования клиента:
- Перечисли ВСЕ бронирования с номерами
- Назови даты, время, количество гостей, столики
- Укажи статусы

Если клиент спрашивает о бронировании:
- Используй информацию о доступных типах столиков
- Предлагай конкретные варианты (у окна, VIP, тихие зоны)
- Учитывай предпочтения клиента

КОНТЕКСТ КЛИЕНТА:
{context}

Ответ (используй информацию из контекста, особенно про столики):
"""
            
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            ai_text = response.text.strip()
            
            print(f"🧠 AI ответ с учетом столиков: {ai_text}")
            return ai_text
            
        except Exception as e:
            print(f"❌ Ошибка получения ответа от ИИ: {e}")
            return None
    
    def get_simple_response(self, user_text, user_name):
        """Простые ответы если ИИ недоступен"""
        text_lower = user_text.lower()
        
        if any(word in text_lower for word in ['привет', 'здравствуй', 'salam']):
            return f"Привет, {user_name}! Добро пожаловать в наш ресторан!"
        
        elif any(word in text_lower for word in ['бронь', 'столик', 'забронировать']):
            # Простая проверка на предпочтения
            if 'окн' in text_lower:
                return "Для столика у окна скажите ваше имя, телефон и количество гостей."
            elif 'vip' in text_lower or 'вип' in text_lower:
                return "Для VIP столика скажите ваше имя, телефон и количество гостей."
            else:
                return "Для бронирования столика скажите ваше имя, телефон и количество гостей. Также можете указать предпочтения: у окна, VIP зона, тихое место."
        
        else:
            return f"Понял! Спасибо за обращение. Чем еще могу помочь?"
    
    async def text_to_speech(self, text):
        """Конвертация текста в голос с обработкой ошибок"""
        try:
            print("🔊 Создаю голосовой ответ...")
            
            if any(char in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for char in text.lower()):
                lang = 'ru'
            else:
                lang = 'az'
            
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_file_path = temp_file.name
            
            try:
                tts = gTTS(text=text, lang=lang, slow=False)
                tts.save(temp_file_path)
                
                with open(temp_file_path, 'rb') as audio_file:
                    audio_data = audio_file.read()
                
                os.unlink(temp_file_path)
                return audio_data
                
            except Exception as network_error:
                print(f"⚠️ Ошибка сети при создании голоса: {network_error}")
                
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                
                return None
            
        except Exception as e:
            print(f"❌ Общая ошибка генерации голоса: {e}")
            return None
    
    def run(self):
        """Запуск бота"""
        print("🚀 Запускаем супер-умного голосового бота с системой столиков...")
        
        application = Application.builder().token(self.telegram_token).build()
        
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(MessageHandler(filters.VOICE, self.handle_voice_message))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        
        print("✅ Бот готов к работе с системой столиков!")
        print("🪑 Умный выбор столиков активен")
        print("🛡️ Fallback логика активна")
        print("🎤 Отправьте голосовое сообщение или напишите текст")
        print("📊 Все проблемные диалоги логируются")
        print("💡 Попробуйте: 'Хочу столик у окна на завтра на 4 человека'")
        print("⚠️ Для остановки нажмите Ctrl+C")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    TELEGRAM_TOKEN = "7210568620:AAFWc4APgOHUBZFhnQSPkHeiOvYpbOPguNY"
    GEMINI_API_KEY = "AIzaSyC2jCwDHrqBEbP2Y4rZZn5EbI4egzPISbc"
    
    print("🚀 Инициализация супер-умного голосового бота с системой столиков...")
    bot = SuperSmartVoiceBot(TELEGRAM_TOKEN, GEMINI_API_KEY)
    bot.run()

if __name__ == "__main__":
    main()