import asyncio
import logging
import tempfile
import os
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
import speech_recognition as sr
from pydub import AudioSegment
from gtts import gTTS
from ai_brain import AIBrain

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SmartVoiceBot:
    """
    Умный голосовой бот с AI Brain
    ИИ полностью управляет диалогом и принимает решения
    """
    
    def __init__(self, telegram_token: str, gemini_key: str):
        self.telegram_token = telegram_token
        
        # Инициализируем AI Brain - мозг системы
        self.ai_brain = AIBrain(gemini_key)
        
        # Распознавание речи
        self.recognizer = sr.Recognizer()
        
        print("🎤 Умный голосовой бот с AI Brain готов!")
        print("🧠 ИИ управляет всем процессом диалога")
        print("🔧 Function Calling активирован")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        
        # Получаем приветствие через AI Brain
        restaurant_info = self.ai_brain._get_restaurant_info()
        
        if restaurant_info.get("success"):
            greeting = restaurant_info.get("greeting", "Добро пожаловать!")
            restaurant_name = restaurant_info.get("name", "Наш ресторан")
            
            welcome_message = f"""
🎙️ {greeting}

🤖 Я умный голосовой помощник ресторана "{restaurant_name}"

Что я умею:
🎤 Понимаю голосовые сообщения на русском языке
🧠 Использую ИИ для принятия решений
🪑 Нахожу и бронирую столики (у окна, VIP, тихие зоны)
📅 Управляю вашими бронированиями
🍽️ Рассказываю о меню
💬 Помню всю историю наших разговоров

Попробуйте сказать:
"Хочу столик у окна на завтра на 4 человека"
"Покажи мое бронирование"
"Какое у вас меню?"

Отправьте голосовое сообщение или напишите текст!
            """
        else:
            welcome_message = "🤖 Добро пожаловать! Я голосовой помощник ресторана. Отправьте голосовое сообщение!"
        
        await update.message.reply_text(welcome_message)
        
        # Сохраняем в истории
        self.ai_brain.save_conversation(user_id, user_name, "/start", welcome_message)
        
        logger.info(f"✅ Пользователь {user_name} (ID: {user_id}) запустил бота")
    
    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка голосовых сообщений через AI Brain"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        
        try:
            logger.info(f"🎤 Получено голосовое сообщение от {user_name}")
            
            await update.message.reply_text("🎤 Обрабатываю ваше голосовое сообщение...")
            
            # Распознаем речь
            voice_file = await update.message.voice.get_file()
            voice_data = await voice_file.download_as_bytearray()
            user_text = await self.speech_to_text(voice_data)
            
            if not user_text:
                await update.message.reply_text("😔 Не удалось распознать речь. Попробуйте еще раз.")
                return
            
            logger.info(f"📝 Распознанный текст: {user_text}")
            await update.message.reply_text(f"✅ Вы сказали: '{user_text}'\n\n🧠 ИИ анализирует запрос...")
            
            # Передаем AI Brain для принятия решений
            await self.process_with_ai_brain(update, user_id, user_name, user_text)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки голоса: {e}")
            await update.message.reply_text("😔 Произошла ошибка при обработке голоса. Попробуйте еще раз.")
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений через AI Brain"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        user_text = update.message.text
        
        logger.info(f"💬 Текстовое сообщение от {user_name}: {user_text}")
        
        await update.message.reply_text("🧠 ИИ анализирует ваш запрос...")
        
        # Передаем AI Brain для принятия решений
        await self.process_with_ai_brain(update, user_id, user_name, user_text)
    
    async def process_with_ai_brain(self, update: Update, user_id: int, user_name: str, user_text: str):
        """Обработка сообщения через AI Brain"""
        try:
            # Получаем историю диалогов
            conversation_history = self.ai_brain.get_conversation_history(user_id)
            
            # AI Brain принимает решения и действует
            ai_response = await self.ai_brain.process_message(user_id, user_text, conversation_history)
            
            # Отправляем ответ пользователю
            await update.message.reply_text(ai_response)
            
            # Создаем голосовой ответ
            voice_response = await self.text_to_speech(ai_response)
            if voice_response:
                await update.message.reply_voice(voice=voice_response)
            
            # Сохраняем диалог
            self.ai_brain.save_conversation(user_id, user_name, user_text, ai_response)
            
            logger.info(f"✅ AI Brain обработал сообщение для {user_name}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка AI Brain: {e}")
            await update.message.reply_text("😔 Произошла ошибка при обработке запроса. Попробуйте еще раз.")
    
    async def speech_to_text(self, audio_data):
        """Распознавание речи"""
        try:
            logger.info("🔄 Распознаю речь...")
            
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # Конвертируем в WAV
            audio = AudioSegment.from_ogg(temp_file_path)
            wav_path = temp_file_path.replace('.ogg', '.wav')
            audio.export(wav_path, format="wav")
            
            # Распознаем
            with sr.AudioFile(wav_path) as source:
                audio_data = self.recognizer.record(source)
            
            try:
                text = self.recognizer.recognize_google(audio_data, language='ru-RU')
                logger.info("🇷🇺 Распознано на русском языке")
                return text
            except sr.UnknownValueError:
                logger.warning("❌ Не удалось распознать речь")
                return None
            finally:
                # Очищаем временные файлы
                os.unlink(temp_file_path)
                os.unlink(wav_path)
            
        except Exception as e:
            logger.error(f"❌ Ошибка распознавания речи: {e}")
            return None
    
    async def text_to_speech(self, text: str):
        """Синтез речи"""
        try:
            logger.info("🔊 Создаю голосовой ответ...")
            
            # Очищаем текст от эмодзи для лучшего синтеза
            clean_text = ''.join(char for char in text if ord(char) < 0x1F600 or ord(char) > 0x1F64F)
            
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_file_path = temp_file.name
            
            # Создаем голос
            tts = gTTS(text=clean_text, lang='ru', slow=False)
            tts.save(temp_file_path)
            
            # Читаем файл
            with open(temp_file_path, 'rb') as audio_file:
                audio_data = audio_file.read()
            
            # Очищаем временный файл
            os.unlink(temp_file_path)
            
            return audio_data
            
        except Exception as e:
            logger.error(f"❌ Ошибка синтеза речи: {e}")
            return None
    
    def run(self):
        """Запуск бота"""
        print("🚀 Запускаю умный голосовой бот с AI Brain...")
        
        application = Application.builder().token(self.telegram_token).build()
        
        # Обработчики
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(MessageHandler(filters.VOICE, self.handle_voice_message))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        
        print("✅ Бот готов к работе!")
        print("🧠 AI Brain управляет всем процессом")
        print("🎤 Отправьте голосовое сообщение или текст")
        print("💡 Попробуйте: 'Хочу столик у окна на завтра на 4 человека'")
        print("⚠️ Для остановки нажмите Ctrl+C")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """Запуск бота"""
    TELEGRAM_TOKEN = "7210568620:AAFWc4APgOHUBZFhnQSPkHeiOvYpbOPguNY"
    GEMINI_API_KEY = "AIzaSyC2jCwDHrqBEbP2Y4rZZn5EbI4egzPISbc"
    
    print("🚀 Инициализация умного голосового бота...")
    bot = SmartVoiceBot(TELEGRAM_TOKEN, GEMINI_API_KEY)
    bot.run()

if __name__ == "__main__":
    main()