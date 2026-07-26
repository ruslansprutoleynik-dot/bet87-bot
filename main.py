
import os
import time
import logging
import requests
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Токен и ID чата Telegram (берутся из переменных окружения Render)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Память для уже отправленных сигналов (чтобы не слать дубликаты)
sent_signals = set()

# Исключаемые ключевые слова (молодежки, женщины, товарищеские матчи)
EXCLUDED_KEYWORDS = [
    "women", "жен", "u17",
    "u18", "u19", "u20", "u21",
    "u23", "reserve", "резерв",
    "friendly", "товарищ",
    "cup", "кубок", "pokal",
    "amateur"
]

# --- Мини-сервер для удержания бота в бодрствующем состоянии на Render ---
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is active and running!")

    def log_message(self, format, *args):
        pass

def run_server():
    server_address = ('0.0.0.0', 10000)
    httpd = HTTPServer(server_address, KeepAliveHandler)
    httpd.serve_forever()

def keep_alive():
    t = Thread(
        target=run_server,
        daemon=True
    )
    t.start()

def send_telegram_message(text):
    """Отправка уведомления в Telegram — канал или чат"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.error("Не заданы TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID!")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logging.error(f"Ошибка отправки в Telegram: {e}")

def main():
    logging.info("Бот запущен и мониторит матчи...")
    
    # Запускаем фоновый веб-сервер для Render
    keep_alive()

    while True:
        # Здесь будет твоя основная логика парсинга/мониторинга
        time.sleep(60)

if __name__ == "__main__":
    main()
