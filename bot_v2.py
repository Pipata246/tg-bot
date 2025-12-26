import os
import logging
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from openai import OpenAI
from dotenv import load_dotenv
import httpx

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Выбор AI провайдера
AI_PROVIDER = os.getenv('AI_PROVIDER', 'test').lower()

# Инициализация клиента
proxy_url = os.getenv('PROXY_URL')

if AI_PROVIDER == 'test':
    client = None
    AI_MODEL = "test"
    logger.info("Используется ТЕСТОВЫЙ режим (без AI)")
elif AI_PROVIDER == 'deepseek':
    client = OpenAI(
        api_key=os.getenv('DEEPSEEK_API_KEY'),
        base_url="https://api.deepseek.com"
    )
    AI_MODEL = "deepseek-chat"
    logger.info("Используется DeepSeek API")
elif AI_PROVIDER == 'groq':
    client = OpenAI(
        api_key=os.getenv('GROQ_API_KEY'),
        base_url="https://api.groq.com/openai/v1"
    )
    AI_MODEL = "llama-3.3-70b-versatile"
    logger.info("Используется Groq API")
else:
    if proxy_url:
        http_client = httpx.Client(proxy=proxy_url)
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'), http_client=http_client)
    else:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    AI_MODEL = "gpt-4o-mini"
    logger.info("Используется OpenAI")

# Хранилище данных пользователей
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - главное меню"""
    keyboard = [
        [InlineKeyboardButton("💬 Чат с AI", callback_data='mode_chat')],
        [InlineKeyboardButton("🖼️ Генерация фото", callback_data='mode_image')],
        [InlineKeyboardButton("🎬 Генерация видео", callback_data='mode_video')],
        [InlineKeyboardButton("🌍 Перевод текста", callback_data='mode_translate')],
        [InlineKeyboardButton("📝 Резюме текста", callback_data='mode_summary')],
        [InlineKeyboardButton("💡 Идеи и советы", callback_data='mode_ideas')],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name
    
    if user_id not in user_data:
        user_data[user_id] = {
            'name': user_name,
            'history': [],
            'mode': None,
            'messages_count': 0
        }
    
    await update.message.reply_text(
        f"👋 Привет, {user_name}!\n\n"
        f"Я многофункциональный AI-бот с возможностями:\n\n"
        f"💬 Умный чат-помощник\n"
        f"🖼️ Генерация изображений\n"
        f"🎬 Создание видео\n"
        f"🌍 Перевод на любой язык\n"
        f"📝 Краткое изложение текстов\n"
        f"💡 Генерация идей\n\n"
        f"Выберите функцию:",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id not in user_data:
        user_data[user_id] = {'history': [], 'mode': None, 'messages_count': 0}
    
    if query.data == 'mode_chat':
        user_data[user_id]['mode'] = 'chat'
        user_data[user_id]['history'] = []
        await query.edit_message_text(
            "💬 Режим: Умный чат\n\n"
            "Задавайте любые вопросы! Я помогу с:\n"
            "• Ответами на вопросы\n"
            "• Решением задач\n"
            "• Объяснениями\n"
            "• Советами\n\n"
            "Команды:\n"
            "/menu - вернуться в меню\n"
            "/clear - очистить историю"
        )
    
    elif query.data == 'mode_image':
        user_data[user_id]['mode'] = 'image'
        await query.edit_message_text(
            "🖼️ Режим: Генерация изображений\n\n"
            "Опишите изображение, которое хотите создать.\n\n"
            "Примеры:\n"
            "• Кот в космосе среди звезд\n"
            "• Футуристический город на закате\n"
            "• Портрет девушки в стиле аниме\n\n"
            "/menu - вернуться в меню"
        )
    
    elif query.data == 'mode_video':
        user_data[user_id]['mode'] = 'video'
        await query.edit_message_text(
            "🎬 Режим: Генерация видео\n\n"
            "Опишите видео, которое хотите создать.\n\n"
            "⚠️ Функция в разработке\n"
            "Скоро будет доступна интеграция с:\n"
            "• Runway ML\n"
            "• Pika Labs\n"
            "• Stability AI Video\n\n"
            "/menu - вернуться в меню"
        )
    
    elif query.data == 'mode_translate':
        user_data[user_id]['mode'] = 'translate'
        await query.edit_message_text(
            "🌍 Режим: Перевод текста\n\n"
            "Отправьте текст в формате:\n"
            "язык: текст\n\n"
            "Примеры:\n"
            "• английский: Привет, как дела?\n"
            "• французский: Hello, how are you?\n"
            "• испанский: Доброе утро\n\n"
            "/menu - вернуться в меню"
        )
    
    elif query.data == 'mode_summary':
        user_data[user_id]['mode'] = 'summary'
        await query.edit_message_text(
            "📝 Режим: Резюме текста\n\n"
            "Отправьте длинный текст, и я создам краткое изложение.\n\n"
            "Полезно для:\n"
            "• Статей\n"
            "• Документов\n"
            "• Новостей\n"
            "• Книг\n\n"
            "/menu - вернуться в меню"
        )
    
    elif query.data == 'mode_ideas':
        user_data[user_id]['mode'] = 'ideas'
        await query.edit_message_text(
            "💡 Режим: Генератор идей\n\n"
            "Опишите тему, и я предложу идеи!\n\n"
            "Примеры:\n"
            "• Идеи для бизнеса в IT\n"
            "• Темы для YouTube канала\n"
            "• Подарки на день рождения\n"
            "• Названия для стартапа\n\n"
            "/menu - вернуться в меню"
        )
    
    elif query.data == 'help':
        await query.edit_message_text(
            "ℹ️ Помощь\n\n"
            "Доступные команды:\n"
            "/start - главное меню\n"
            "/menu - показать меню\n"
            "/clear - очистить историю\n"
            "/stats - статистика использования\n\n"
            "Режимы работы:\n"
            "💬 Чат - общение с AI\n"
            "🖼️ Фото - генерация изображений\n"
            "🎬 Видео - создание видео\n"
            "🌍 Перевод - перевод текстов\n"
            "📝 Резюме - краткое изложение\n"
            "💡 Идеи - генерация идей\n\n"
            "/menu - вернуться в меню"
        )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /menu"""
    keyboard = [
        [InlineKeyboardButton("💬 Чат с AI", callback_data='mode_chat')],
        [InlineKeyboardButton("🖼️ Генерация фото", callback_data='mode_image')],
        [InlineKeyboardButton("🎬 Генерация видео", callback_data='mode_video')],
        [InlineKeyboardButton("🌍 Перевод текста", callback_data='mode_translate')],
        [InlineKeyboardButton("📝 Резюме текста", callback_data='mode_summary')],
        [InlineKeyboardButton("💡 Идеи и советы", callback_data='mode_ideas')],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите функцию:", reply_markup=reply_markup)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика пользователя"""
    user_id = update.message.from_user.id
    
    if user_id not in user_data:
        await update.message.reply_text("У вас пока нет статистики. Начните использовать бота!")
        return
    
    data = user_data[user_id]
    await update.message.reply_text(
        f"📊 Ваша статистика:\n\n"
        f"👤 Имя: {data.get('name', 'Неизвестно')}\n"
        f"💬 Сообщений отправлено: {data.get('messages_count', 0)}\n"
        f"🕐 Текущий режим: {data.get('mode', 'Не выбран')}\n"
        f"📝 Сообщений в истории: {len(data.get('history', []))}"
    )

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очистка истории"""
    user_id = update.message.from_user.id
    if user_id in user_data:
        user_data[user_id]['history'] = []
        await update.message.reply_text("✅ История очищена!")
    else:
        await update.message.reply_text("История уже пуста")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений"""
    user_id = update.message.from_user.id
    message = update.message.text
    
    if user_id not in user_data:
        await update.message.reply_text("Используйте /start для начала работы")
        return
    
    mode = user_data[user_id].get('mode')
    user_data[user_id]['messages_count'] = user_data[user_id].get('messages_count', 0) + 1
    
    try:
        if mode == 'chat':
            await handle_chat(update, user_id, message)
        elif mode == 'image':
            await handle_image(update, message)
        elif mode == 'video':
            await handle_video(update, message)
        elif mode == 'translate':
            await handle_translate(update, user_id, message)
        elif mode == 'summary':
            await handle_summary(update, user_id, message)
        elif mode == 'ideas':
            await handle_ideas(update, user_id, message)
        else:
            await update.message.reply_text("Выберите режим с помощью /menu")
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(
            f"❌ Ошибка: {str(e)}\n\n"
            "Попробуйте еще раз или используйте /menu"
        )

async def handle_chat(update: Update, user_id: int, message: str):
    """Обработка чата"""
    if AI_PROVIDER == 'test':
        await update.message.reply_text(
            f"🤖 ТЕСТОВЫЙ РЕЖИМ\n\n"
            f"Вы: {message}\n\n"
            f"Бот работает! Для подключения AI добавьте API ключ в .env"
        )
        return
    
    user_data[user_id]['history'].append({"role": "user", "content": message})
    
    if len(user_data[user_id]['history']) > 20:
        user_data[user_id]['history'] = user_data[user_id]['history'][-20:]
    
    await update.message.reply_text("⏳ Думаю...")
    
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=user_data[user_id]['history'],
        max_tokens=1000
    )
    
    answer = response.choices[0].message.content
    user_data[user_id]['history'].append({"role": "assistant", "content": answer})
    
    await update.message.reply_text(answer)

async def handle_image(update: Update, prompt: str):
    """Генерация изображений"""
    if AI_PROVIDER != 'openai':
        await update.message.reply_text(
            "⚠️ Генерация изображений доступна только с OpenAI API\n\n"
            "Установите AI_PROVIDER=openai в .env"
        )
        return
    
    await update.message.reply_text("🎨 Генерирую изображение...")
    
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1
    )
    
    await update.message.reply_photo(
        photo=response.data[0].url,
        caption=f"🖼️ Готово!\n\nЗапрос: {prompt}"
    )

async def handle_video(update: Update, prompt: str):
    """Генерация видео"""
    await update.message.reply_text(
        f"🎬 Генерация видео...\n\n"
        f"⚠️ Функция в разработке\n\n"
        f"Ваш запрос: {prompt}\n\n"
        f"Скоро будет доступна!"
    )

async def handle_translate(update: Update, user_id: int, message: str):
    """Перевод текста"""
    if AI_PROVIDER == 'test':
        await update.message.reply_text(
            f"🌍 ТЕСТОВЫЙ РЕЖИМ\n\n"
            f"Перевод: {message}\n\n"
            f"Для работы нужен API ключ"
        )
        return
    
    await update.message.reply_text("🌍 Перевожу...")
    
    prompt = f"Переведи следующий текст: {message}. Определи язык автоматически и переведи на указанный язык."
    
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    
    await update.message.reply_text(f"✅ Перевод:\n\n{response.choices[0].message.content}")

async def handle_summary(update: Update, user_id: int, message: str):
    """Резюме текста"""
    if AI_PROVIDER == 'test':
        await update.message.reply_text(
            f"📝 ТЕСТОВЫЙ РЕЖИМ\n\n"
            f"Краткое изложение вашего текста будет здесь\n\n"
            f"Для работы нужен API ключ"
        )
        return
    
    await update.message.reply_text("📝 Создаю краткое изложение...")
    
    prompt = f"Создай краткое и понятное резюме следующего текста:\n\n{message}"
    
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    
    await update.message.reply_text(f"📝 Краткое изложение:\n\n{response.choices[0].message.content}")

async def handle_ideas(update: Update, user_id: int, message: str):
    """Генерация идей"""
    if AI_PROVIDER == 'test':
        await update.message.reply_text(
            f"💡 ТЕСТОВЫЙ РЕЖИМ\n\n"
            f"Идеи по теме: {message}\n\n"
            f"1. Идея 1\n"
            f"2. Идея 2\n"
            f"3. Идея 3\n\n"
            f"Для работы нужен API ключ"
        )
        return
    
    await update.message.reply_text("💡 Генерирую идеи...")
    
    prompt = f"Предложи 5 креативных и практичных идей на тему: {message}"
    
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800
    )
    
    await update.message.reply_text(f"💡 Идеи:\n\n{response.choices[0].message.content}")

def main():
    """Запуск бота"""
    import asyncio
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не найден!")
        return
    
    application = Application.builder().token(token).build()
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("clear", clear_history))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🚀 Бот v2 запущен!")
    
    # Фикс для Python 3.14
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
