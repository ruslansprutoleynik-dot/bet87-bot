import os
import asyncio
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Санитаризация переменных окружения (удаляем лишние пробелы и \n)
BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
PROXY_URL = (os.getenv("PROXY_URL") or "").strip()

# Проверка наличия токена
if not BOT_TOKEN:
    logger.error("ОШИБКА: Переменная BOT_TOKEN не найдена или пуста!")

# Настройки прокси
PROXIES = None
if PROXY_URL:
    logger.info(f"Используем прокси: {PROXY_URL}")
    PROXIES = {
        "http": PROXY_URL,
        "https": PROXY_URL
    }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Бот успешно запущен и работает!")

def main():
    if not BOT_TOKEN:
        print("Ошибка: Токен бота отсутствует. Завершение работы.")
        return

    # Создаем объект приложения
    builder = Application.builder().token(BOT_TOKEN)
    
    # Если задан прокси, добавляем его в запросы
    if PROXIES:
        builder.request_kwargs({"proxies": PROXIES})

    app = builder.build()

    # Регистрируем команды
    app.add_handler(CommandHandler("start", start))

    print("Бот запущен и ожидает сообщений...")
    app.run_polling()

if __name__ == "__main__":
    main()
