import os
import asyncio
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN", "8948155468:AAGGnRuzXi0EqtnuY6K1O6_wvg8BFMz5dDY")
PROXY_URL = os.getenv("PROXY_URL", "http://ryiutsiz:0zakv2546ezu@31.59.20.176:6754")

# Настройки запросов через прокси
PROXIES = {
    "http": PROXY_URL,
    "https": PROXY_URL
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Бот мониторинга матчей (83'-87' мин) запущен и работает 24/7!")

async def monitor_matches(app: Application):
    """Фоновая задача для проверки матчей каждые 60 секунд."""
    while True:
        try:
            # Здесь будет логика запроса к API парсера
            logger.info("Проверка матчей на 83-87 минутах...")
        except Exception as e:
            logger.error(f"Ошибка при мониторинге: {e}")
        await asyncio.sleep(60)

async def post_init(app: Application):
    asyncio.create_task(monitor_matches(app))

def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    
    logger.info("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
