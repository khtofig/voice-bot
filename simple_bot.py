import asyncio
import logging
import tempfile
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler, CallbackQueryHandler
import speech_recognition as sr
from pydub import AudioSegment
from gtts import gTTS
import google.generativeai as genai
from database import RestaurantDatabase

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class RestaurantBotWithDatabase:
    def __init__(self, telegram_token, gemini_key):
        self.telegram_token = telegram_token
        self.gemini_key = gemini_key
        
        # Подключаем базу данных
        self.db = RestaurantDatabase()
        print("💾 База данных подключена к боту")
        
        # Настройка Gemini
        if gemini_key and gemini_key != "ВСТАВЬТЕ_ВАШ_КЛЮЧ":
            genai.configure(api_key=self.gemini_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            print("🤖 Gemini AI подключен")
        else:
            self.model = None
            print("⚠️ Gemini AI не подключен (работаю в простом режиме)")
        
        # Настройка распознавания речи
        self.recognizer = sr.Recognizer()
        
        print("✅ Бот с базой данных готов!")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Главное меню - ТЕПЕРЬ ЧИТАЕТ ИЗ БАЗЫ"""
        # Получаем данные ресторана из базы
        restaurant_data = self.db.get_restaurant_data()
        
        if not restaurant_data:
            await update.message.reply_text("❌ Ресторан не найден в базе данных")
            return
        
        # Распаковываем данные
        name, phone, address, working_hours, greeting_message, ai_personality = restaurant_data
        
        keyboard = [
            [InlineKeyboardButton("📞 Имитация звонка клиента", callback_data="demo_call")],
            [InlineKeyboardButton("🍽️ Показать меню из базы", callback_data="show_menu")],
            [InlineKeyboardButton("ℹ️ Информация о ресторане", callback_data="restaurant_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_message = f"""
🤖 <b>Голосовой помощник ресторана</b>

<b>💾 ДАННЫЕ ИЗ БАЗЫ:</b>

🏪 <b>Ресторан:</b> {name}
📞 <b>Телефон:</b> {phone}
📍 <b>Адрес:</b> {address}
⏰ <b>Часы работы:</b> {working_hours}

🤖 <b>Настройки ИИ:</b>
<i>"{ai_personality}"</i>

<b>💬 Приветствие бота:</b>
<i>"{greeting_message}"</i>

✅ <b>Все данные загружены из базы данных!</b>
        """
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='HTML')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопок"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "demo_call":
            await self.start_demo_call(query)
        elif query.data == "show_menu":
            await self.show_menu_from_db(query)
        elif query.data == "restaurant_info":
            await self.show_restaurant_info(query)
        elif query.data == "back_to_main":  # ← ДОБАВЬТЕ ЭТУ СТРОКУ
            await self.show_main_menu(query)  # ← И ЭТУ   
         
    
    async def start_demo_call(self, query):
        """Демо-звонок - приветствие ИЗ БАЗЫ"""
        restaurant_data = self.db.get_restaurant_data()
        greeting_message = restaurant_data[4]  # greeting_message
        
        await query.edit_message_text(f"""
📞 <b>ДЕМО-ЗВОНОК НАЧАТ</b>

🤖 <b>Бот отвечает (приветствие из базы):</b>
"{greeting_message}"

🎤 <b>Отправьте голосовое сообщение как клиент</b>

<i>Бот будет использовать данные ресторана из базы для ответов</i>
        """, parse_mode='HTML')
        
        # Отправляем голосовое приветствие
        greeting_audio = await self.text_to_speech(greeting_message)
        if greeting_audio:
            await query.message.reply_voice(voice=greeting_audio)
    
    async def show_menu_from_db(self, query):
        """Показать меню ИЗ БАЗЫ ДАННЫХ"""
        menu_items = self.db.get_menu_items()
        
        if not menu_items:
            await query.edit_message_text("📋 Меню пока не добавлено в базу")
            return
        
        menu_text = "🍽️ <b>Меню ресторана (из базы данных):</b>\n\n"
        
        current_category = ""
        for category, name, description, price in menu_items:
            if category != current_category:
                menu_text += f"\n<b>🔸 {category}:</b>\n"
                current_category = category
            
            menu_text += f"• <b>{name}</b> - {price}₽\n"
            if description:
                menu_text += f"  <i>{description}</i>\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад в главное меню", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def show_restaurant_info(self, query):
        """Показать информацию о ресторане из базы"""
        restaurant_data = self.db.get_restaurant_data()
        name, phone, address, working_hours, greeting_message, ai_personality = restaurant_data
        
        info_text = f"""
    
🏪 <b>Информация о ресторане</b>
<i>(данные из базы)</i>

📛 <b>Название:</b> {name}
📞 <b>Телефон:</b> {phone}
📍 <b>Адрес:</b> {address}
⏰ <b>Время работы:</b> {working_hours}

🤖 <b>Настройки бота:</b>
<b>Личность ИИ:</b> {ai_personality}

<b>Приветствие:</b> {greeting_message}
        """
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(info_text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def show_main_menu(self, query):
        """Показать главное меню"""
        # Получаем данные ресторана из базы
        restaurant_data = self.db.get_restaurant_data()
        
        if not restaurant_data:
            await query.edit_message_text("❌ Ресторан не найден в базе данных")
            return
        
        # Распаковываем данные
        name, phone, address, working_hours, greeting_message, ai_personality = restaurant_data
        
        keyboard = [
            [InlineKeyboardButton("📞 Имитация звонка клиента", callback_data="demo_call")],
            [InlineKeyboardButton("🍽️ Показать меню из базы", callback_data="show_menu")],
            [InlineKeyboardButton("ℹ️ Информация о ресторане", callback_data="restaurant_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_message = f"""
🤖 <b>Голосовой помощник ресторана</b>

<b>💾 ДАННЫЕ ИЗ БАЗЫ:</b>

🏪 <b>Ресторан:</b> {name}
📞 <b>Телефон:</b> {phone}
📍 <b>Адрес:</b> {address}
⏰ <b>Часы работы:</b> {working_hours}

🤖 <b>Настройки ИИ:</b>
<i>"{ai_personality}"</i>

<b>💬 Приветствие бота:</b>
<i>"{greeting_message}"</i>

✅ <b>Все данные загружены из базы данных!</b>
        """
        
        await query.edit_message_text(welcome_message, reply_markup=reply_markup, parse_mode='HTML')
    
    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка голосовых сообщений С ДАННЫМИ ИЗ БАЗЫ"""
        try:
            await update.message.reply_text("🎤 Обрабатываю ваш запрос...")
            
            # Распознаем речь
            voice_file = await update.message.voice.get_file()
            voice_data = await voice_file.download_as_bytearray()
            customer_text = await self.speech_to_text(voice_data)
            
            if not customer_text:
                await update.message.reply_text("😔 Не удалось распознать речь")
                return
            
            await update.message.reply_text(f"👤 <b>Клиент сказал:</b> {customer_text}", parse_mode='HTML')
            
            # Генерируем ответ ИСПОЛЬЗУЯ ДАННЫЕ ИЗ БАЗЫ
            bot_response = await self.generate_response_from_database(customer_text)
            
            await update.message.reply_text(f"🤖 <b>Бот отвечает:</b> {bot_response}", parse_mode='HTML')
            
            # Озвучиваем ответ
            response_audio = await self.text_to_speech(bot_response)
            if response_audio:
                await update.message.reply_voice(voice=response_audio)
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            await update.message.reply_text("😔 Произошла ошибка при обработке голоса")
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        try:
            customer_text = update.message.text
            await update.message.reply_text(f"👤 <b>Клиент написал:</b> {customer_text}", parse_mode='HTML')
        
            # Генерируем ответ используя данные из базы
            bot_response = await self.generate_response_from_database(customer_text)
        
            await update.message.reply_text(f"🤖 <b>Бот отвечает:</b> {bot_response}", parse_mode='HTML')
        
            # Можете также озвучить ответ
            response_audio = await self.text_to_speech(bot_response)
            if response_audio:
                await update.message.reply_voice(voice=response_audio)
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            await update.message.reply_text("😔 Произошла ошибка при обработке сообщения")
    
    async def generate_response_from_database(self, customer_text):
        """Генерация ответа ИСПОЛЬЗУЯ ДАННЫЕ ИЗ БАЗЫ"""
        # Получаем данные ресторана из базы
        restaurant_data = self.db.get_restaurant_data()
        menu_items = self.db.get_menu_items()
        
        # Распаковываем данные
        name, phone, address, working_hours, greeting_message, ai_personality = restaurant_data
        
        # Формируем информацию о меню
        menu_text = ""
        for category, item_name, description, price in menu_items[:5]:  # Берем первые 5 блюд
            menu_text += f"- {item_name}: {price}₽ ({description})\n"
        
        # Если есть Gemini AI
        if self.model:
            prompt = f"""
Ты {ai_personality} ресторана "{name}".

ИНФОРМАЦИЯ О РЕСТОРАНЕ (из базы данных):
- Название: {name}
- Телефон: {phone}
- Адрес: {address}
- Время работы: {working_hours}

НАШЕ МЕНЮ:
{menu_text}

КЛИЕНТ СКАЗАЛ: "{customer_text}"

Ответь как {ai_personality}. Используй информацию о ресторане.
Помоги клиенту забронировать столик или ответь на его вопрос.
Отвечай кратко (до 50 слов) и естественно.
            """
            
            try:
                response = await asyncio.to_thread(self.model.generate_content, prompt)
                return response.text.strip()
            except Exception as e:
                print(f"❌ Ошибка Gemini: {e}")
        
        # Простой ответ если ИИ недоступен
        if "меню" in customer_text.lower():
            return f"У нас есть: {menu_items[0][1]} за {menu_items[0][3]}₽, {menu_items[1][1]} за {menu_items[1][3]}₽ и другие блюда."
        elif "время" in customer_text.lower() or "работа" in customer_text.lower():
            return f"Мы работаем {working_hours}."
        elif "адрес" in customer_text.lower():
            return f"Наш адрес: {address}."
        else:
            return f"Понял! Помогу забронировать столик в ресторане {name}. Уточните количество гостей и время."
    
    # Методы для работы с голосом (те же что были)
    async def speech_to_text(self, audio_data):
        """Распознавание речи"""
        try:
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
            except sr.UnknownValueError:
                text = None
            
            os.unlink(temp_file_path)
            os.unlink(wav_path)
            return text
            
        except Exception as e:
            print(f"❌ Ошибка распознавания: {e}")
            return None
    
    async def text_to_speech(self, text):
        """Синтез речи"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_file_path = temp_file.name
            
            tts = gTTS(text=text, lang='ru', slow=False)
            tts.save(temp_file_path)
            
            with open(temp_file_path, 'rb') as audio_file:
                audio_data = audio_file.read()
            
            os.unlink(temp_file_path)
            return audio_data
            
        except Exception as e:
            print(f"❌ Ошибка синтеза: {e}")
            return None
    
    def run(self):
        """Запуск бота"""
        application = Application.builder().token(self.telegram_token).build()
        
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CallbackQueryHandler(self.button_callback))
        application.add_handler(MessageHandler(filters.VOICE, self.handle_voice_message))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))  # ← ДОБАВЬТЕ ЭТУ СТРОКУ
        
        print("🤖 Бот запущен и читает данные из базы!")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

# Запуск бота
if __name__ == "__main__":
    TELEGRAM_TOKEN = "7210568620:AAFWc4APgOHUBZFhnQSPkHeiOvYpbOPguNY"  # Замените на ваш токен
    GEMINI_API_KEY = "AIzaSyC2jCwDHrqBEbP2Y4rZZn5EbI4egzPISbc"  # Замените на ваш ключ
    
    bot = RestaurantBotWithDatabase(TELEGRAM_TOKEN, GEMINI_API_KEY)
    bot.run()