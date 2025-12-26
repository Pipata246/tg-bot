import os
import logging
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
AI_PROVIDER = os.getenv('AI_PROVIDER', 'deepseek').lower()

# Инициализация клиента в зависимости от провайдера
proxy_url = os.getenv('PROXY_URL')

if AI_PROVIDER == 'test':
    # Тестовый режим без AI
    client = None
    AI_MODEL = "test"
    logger.info("Используется ТЕСТОВЫЙ режим (без AI)")

elif AI_PROVIDER == 'free':
    # Бесплатный API без регистрации (g4f)
    import g4f
    client = None
    AI_MODEL = "gpt-3.5-turbo"
    logger.info("Используется бесплатный API (без регистрации)")

elif AI_PROVIDER == 'huggingface':
    # HuggingFace API (бесплатный)
    client = OpenAI(
        api_key=os.getenv('HUGGINGFACE_API_KEY', 'hf_dummy'),
        base_url="https://router.huggingface.co/v1"
    )
    AI_MODEL = "meta-llama/Llama-3.2-3B-Instruct"
    logger.info("Используется HuggingFace API")

elif AI_PROVIDER == 'together':
    # Together AI (бесплатный)
    client = OpenAI(
        api_key=os.getenv('TOGETHER_API_KEY'),
        base_url="https://api.together.xyz/v1"
    )
    AI_MODEL = "meta-llama/Llama-3-8b-chat-hf"
    logger.info("Используется Together AI")
    
elif AI_PROVIDER == 'deepseek':
    # DeepSeek API (бесплатный)
    if proxy_url:
        http_client = httpx.Client(proxy=proxy_url)
        client = OpenAI(
            api_key=os.getenv('DEEPSEEK_API_KEY', 'dummy'),
            base_url="https://api.deepseek.com",
            http_client=http_client
        )
    else:
        client = OpenAI(
            api_key=os.getenv('DEEPSEEK_API_KEY', 'dummy'),
            base_url="https://api.deepseek.com"
        )
    AI_MODEL = "deepseek-chat"
    logger.info(f"Используется DeepSeek API")
    
elif AI_PROVIDER == 'groq':
    # Groq API (бесплатный, очень быстрый)
    if proxy_url:
        http_client = httpx.Client(proxy=proxy_url)
        client = OpenAI(
            api_key=os.getenv('GROQ_API_KEY'),
            base_url="https://api.groq.com/openai/v1",
            http_client=http_client
        )
    else:
        client = OpenAI(
            api_key=os.getenv('GROQ_API_KEY'),
            base_url="https://api.groq.com/openai/v1"
        )
    AI_MODEL = "llama-3.3-70b-versatile"
    logger.info(f"Используется Groq API")
    
else:
    # OpenAI (платный)
    if proxy_url:
        http_client = httpx.Client(proxy=proxy_url)
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'), http_client=http_client)
        logger.info(f"Используется OpenAI с прокси: {proxy_url}")
    else:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        logger.info("Используется OpenAI")
    AI_MODEL = "gpt-4o-mini"

if proxy_url:
    logger.info(f"Прокси: {proxy_url}")

# Хранилище контекста пользователей
user_contexts = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - приветствие и меню"""
    keyboard = [
        [InlineKeyboardButton("💬 Чат с AI", callback_data='mode_chat')],
        [InlineKeyboardButton("🖼️ Генерация фото", callback_data='mode_image')],
        [InlineKeyboardButton("🌍 Перевод текста", callback_data='mode_translate')],
        [InlineKeyboardButton("📝 Резюме текста", callback_data='mode_summary')],
        [InlineKeyboardButton("💡 Генератор идей", callback_data='mode_ideas')],
        [InlineKeyboardButton("🎬 Генерация видео", callback_data='mode_video')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 Привет! Я многофункциональный AI-бот:\n\n"
        "💬 Умный чат-помощник\n"
        "🖼️ Генерация изображений\n"
        "🌍 Перевод на любой язык\n"
        "📝 Краткое изложение текстов\n"
        "💡 Генерация креативных идей\n"
        "🎬 Создание видео\n\n"
        "Выберите функцию:",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == 'mode_chat':
        user_contexts[user_id] = {'mode': 'chat', 'history': []}
        await query.edit_message_text(
            "💬 Режим: Текстовый помощник\n\n"
            "Задавайте любые вопросы, я отвечу как ChatGPT!\n\n"
            "Используйте /menu для смены режима"
        )
    
    elif query.data == 'mode_image':
        user_contexts[user_id] = {'mode': 'image'}
        await query.edit_message_text(
            "🖼️ Режим: Генерация изображений\n\n"
            "Опишите изображение, которое хотите создать.\n"
            "Например: 'кот в космосе с планетами'\n\n"
            "Используйте /menu для смены режима"
        )
    
    elif query.data == 'mode_translate':
        user_contexts[user_id] = {'mode': 'translate'}
        await query.edit_message_text(
            "🌍 Режим: Перевод текста\n\n"
            "Формат: язык: текст\n\n"
            "Примеры:\n"
            "• английский: Привет!\n"
            "• французский: Hello!\n\n"
            "/menu - вернуться в меню"
        )
    
    elif query.data == 'mode_summary':
        user_contexts[user_id] = {'mode': 'summary'}
        await query.edit_message_text(
            "📝 Режим: Резюме текста\n\n"
            "Отправьте длинный текст, и я создам краткое изложение.\n\n"
            "/menu - вернуться в меню"
        )
    
    elif query.data == 'mode_ideas':
        user_contexts[user_id] = {'mode': 'ideas'}
        await query.edit_message_text(
            "💡 Режим: Генератор идей\n\n"
            "Опишите тему, и я предложу идеи!\n\n"
            "Примеры:\n"
            "• Идеи для бизнеса\n"
            "• Темы для YouTube\n"
            "• Подарки на праздник\n\n"
            "/menu - вернуться в меню"
        )
    
    elif query.data == 'mode_video':
        user_contexts[user_id] = {'mode': 'video'}
        await query.edit_message_text(
            "🎬 Режим: Генерация видео\n\n"
            "Опишите видео, которое хотите создать.\n\n"
            "⚠️ Функция в разработке\n\n"
            "/menu - вернуться в меню"
        )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /menu - показать меню выбора режима"""
    keyboard = [
        [InlineKeyboardButton("💬 Текстовый помощник", callback_data='mode_chat')],
        [InlineKeyboardButton("🖼️ Генерация фото", callback_data='mode_image')],
        [InlineKeyboardButton("🎬 Генерация видео", callback_data='mode_video')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Выберите режим работы:",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    user_id = update.message.from_user.id
    user_message = update.message.text
    
    # Проверка режима пользователя
    if user_id not in user_contexts:
        await update.message.reply_text(
            "Пожалуйста, выберите режим работы с помощью /start или /menu"
        )
        return
    
    mode = user_contexts[user_id]['mode']
    
    try:
        if mode == 'chat':
            await handle_chat(update, user_id, user_message)
        elif mode == 'image':
            await handle_image_generation(update, user_message)
        elif mode == 'translate':
            await handle_translate(update, user_id, user_message)
        elif mode == 'summary':
            await handle_summary(update, user_id, user_message)
        elif mode == 'ideas':
            await handle_ideas(update, user_id, user_message)
        elif mode == 'video':
            await handle_video_generation(update, user_message)
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(
            f"❌ Произошла ошибка: {str(e)}\n\n"
            "Попробуйте еще раз или используйте /menu для смены режима"
        )

async def handle_chat(update: Update, user_id: int, message: str):
    """Обработка текстового чата (ChatGPT)"""
    # Тестовый режим
    if AI_PROVIDER == 'test':
        await update.message.reply_text(
            f"🤖 ТЕСТОВЫЙ РЕЖИМ\n\n"
            f"Вы написали: {message}\n\n"
            f"Бот работает! Но AI не подключен.\n"
            f"Чтобы подключить AI:\n"
            f"1. Получите ключ на console.groq.com\n"
            f"2. Добавьте в .env: GROQ_API_KEY=ваш_ключ\n"
            f"3. Установите: AI_PROVIDER=groq\n"
            f"4. Перезапустите бота"
        )
        return
    
    # Добавление сообщения в историю
    if 'history' not in user_contexts[user_id]:
        user_contexts[user_id]['history'] = []
    
    user_contexts[user_id]['history'].append({
        "role": "user",
        "content": message
    })
    
    # Ограничение истории (последние 10 сообщений)
    if len(user_contexts[user_id]['history']) > 20:
        user_contexts[user_id]['history'] = user_contexts[user_id]['history'][-20:]
    
    # Отправка запроса к OpenAI
    await update.message.reply_text("⏳ Думаю...")
    
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=user_contexts[user_id]['history'],
        max_tokens=1000
    )
    
    assistant_message = response.choices[0].message.content
    
    # Добавление ответа в историю
    user_contexts[user_id]['history'].append({
        "role": "assistant",
        "content": assistant_message
    })
    
    await update.message.reply_text(assistant_message)

async def handle_image_generation(update: Update, prompt: str):
    """Генерация изображения (DALL-E)"""
    if AI_PROVIDER != 'openai':
        await update.message.reply_text(
            "⚠️ Генерация изображений доступна только с OpenAI API.\n\n"
            "Для использования этой функции:\n"
            "1. Получите OpenAI API ключ\n"
            "2. Установите AI_PROVIDER=openai в .env\n"
            "3. Пополните баланс на platform.openai.com"
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
    
    image_url = response.data[0].url
    
    await update.message.reply_photo(
        photo=image_url,
        caption=f"🖼️ Ваше изображение готово!\n\nЗапрос: {prompt}"
    )

async def handle_video_generation(update: Update, prompt: str):
    """Генерация видео (заглушка для будущей интеграции)"""
    await update.message.reply_text(
        "🎬 Генерация видео...\n\n"
        "⚠️ Функция в разработке!\n\n"
        "Для генерации видео можно интегрировать:\n"
        "- Runway ML API\n"
        "- Stability AI Video\n"
        "- Pika Labs API\n\n"
        f"Ваш запрос: {prompt}"
    )

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /clear - очистка истории чата"""
    user_id = update.message.from_user.id
    if user_id in user_contexts and 'history' in user_contexts[user_id]:
        user_contexts[user_id]['history'] = []
        await update.message.reply_text("✅ История чата очищена")
    else:
        await update.message.reply_text("История уже пуста")

async def handle_translate(update: Update, user_id: int, message: str):
    """Перевод текста"""
    if AI_PROVIDER == 'test':
        await update.message.reply_text(
            f"🌍 ТЕСТОВЫЙ РЕЖИМ\n\nПеревод: {message}\n\nДля работы нужен API ключ"
        )
        return
    
    await update.message.reply_text("🌍 Перевожу...")
    prompt = f"Переведи текст: {message}"
    
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    
    await update.message.reply_text(f"✅ {response.choices[0].message.content}")

async def handle_summary(update: Update, user_id: int, message: str):
    """Резюме текста"""
    if AI_PROVIDER == 'test':
        await update.message.reply_text(
            f"📝 ТЕСТОВЫЙ РЕЖИМ\n\nКраткое изложение вашего текста\n\nДля работы нужен API ключ"
        )
        return
    
    await update.message.reply_text("📝 Создаю резюме...")
    prompt = f"Создай краткое резюме текста:\n\n{message}"
    
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    
    await update.message.reply_text(f"📝 Резюме:\n\n{response.choices[0].message.content}")

async def handle_ideas(update: Update, user_id: int, message: str):
    """Генерация идей"""
    if AI_PROVIDER == 'test':
        await update.message.reply_text(
            f"💡 ТЕСТОВЫЙ РЕЖИМ\n\nИдеи по теме: {message}\n\n1. Идея 1\n2. Идея 2\n3. Идея 3\n\nДля работы нужен API ключ"
        )
        return
    
    await update.message.reply_text("💡 Генерирую идеи...")
    prompt = f"Предложи 5 креативных идей на тему: {message}"
    
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800
    )
    
    await update.message.reply_text(f"💡 Идеи:\n\n{response.choices[0].message.content}")

def main():
    """Запуск бота"""
    import asyncio
    
    # Получение токена бота
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
        return
    
    # Создание приложения
    application = Application.builder().token(token).build()
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("clear", clear_history))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запуск бота
    logger.info("Бот запущен!")
    
    # Фикс для Python 3.14
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
