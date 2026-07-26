import os
import time
import logging
import requests
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# Настройка логирования для вывода в консоль Render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Множество для защиты от повторной отправки сигналов по тому же матчу
sent_signals = set()

# Стоп-слова для исключения нежелательных лиг
EXCLUDED_KEYWORDS = [
    "women", "жен", "u17", "u18", "u19", "u20", "u21", "u23", 
    "reserve", "резерв", "friendly", "товарищ", "cup", "кубок", 
    "pokal", "amateur"
]

# Строго разрешенные счета цифрами
ALLOWED_SCORES = {
    "1:0", "0:1",
    "2:1", "1:2",
    "3:2", "2:3",
    "4:3", "3:4",
    "5:4", "4:5",
    "6:5", "5:6",
    "2:0", "0:2",
    "3:1", "1:3",
    "4:2", "2:4",
    "5:3", "3:5",
    "6:4", "4:6"
}

class KeepAliveHandler(BaseHTTPRequestHandler):
    """Веб-сервер для предотвращения засыпания на Render (порт 10000)"""
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
    """Запуск веб-сервера в фоновом потоке"""
    t = Thread(target=run_server, daemon=True)
    t.start()

def send_telegram_message(text):
    """Надежная отправка уведомлений в Telegram с обработкой ошибок"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.error("ОШИБКА: Не заданы TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID в переменных окружения!")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN.strip()}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID.strip(),
        "text": text,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            logging.info("Сообщение успешно отправлено в Telegram.")
            return True
        else:
            logging.error(f"Telegram API вернул ошибку {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logging.error(f"Сетевая ошибка при отправке в Telegram: {e}")
        return False

def check_matches():
    """Логика сканирования матчей (77-87 мин, фильтры лиг и счетов)"""
    try:
        logging.info("Цикл сканирования матчей активен...")
        # Сюда будет интегрирована логика парсинга данных о матчах
    except Exception as e:
        logging.error(f"Ошибка при сканировании матчей: {e}")

def main():
    logging.info("Инициализация бота...")
    
    # 1. Запускаем анти-сон сервер
    keep_alive()
    logging.info("Сервер анти-сна запущен на порту 10000.")

    # Даем серверу секунду на инициализацию
    time.sleep(2)

    # 2. Тестовая отправка сообщения при запуске
    logging.info("Попытка отправить стартовое сообщение в Telegram...")
    send_telegram_message("🟢 Бот успешно запущен на Render! Мониторинг матчей (77-87 мин) активирован.")

    # 3. Основной цикл работы
    while True:
        check_matches()
        time.sleep(30)

if __name__ == '__main__':
    main()
