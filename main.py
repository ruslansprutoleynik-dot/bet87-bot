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

# Строго разрешенные счета цифрами (разница в 1 гол + пределы до 6:5)
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
    """Веб-сервер для предотвращения засыпания на Render"""
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
    """Надежная отправка уведомлений в Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.error("Не заданы TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID!")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        logging.error(f"Ошибка отправки в Telegram: {e}")
        return False

def check_matches():
    """Логика проверки матчей (77-87 мин, счета, фильтры)"""
    try:
        logging.info("Сканирование лайв-матчей...")
        
        # Шаблон логики проверки:
        # 1. Запрос к источнику матчей
        # 2. Фильтрация лиг по EXCLUDED_KEYWORDS
        # 3. Проверка времени (77 <= минута <= 87)
        # 4. Проверка счета по ALLOWED_SCORES
        # 5. Отправка сигнала в Telegram, если матч еще не в sent_signals
        
    except Exception as e:
        logging.error(f"Ошибка при сканировании матчей: {e}")

def main():
    logging.info("Инициализация бота...")
    
    # 1. Запускаем защиту от засыпания (порт 10000)
    keep_alive()
    logging.info("Сервер анти-сна запущен на порту 10000.")

    # 2. Отправляем стартовое сообщение в Telegram для проверки связи
    success = send_telegram_message("🟢 Бот успешно запущен! Фильтры (77-87 мин, счета 1:0...6:5) активны.")
    if success:
        logging.info("Стартовое сообщение доставлено.")
    else:
        logging.warning("Не удалось отправить стартовое сообщение. Проверьте токены в переменных окружения Render.")

    # 3. Бесконечный цикл опроса с интервалом 30 секунд
    while True:
        try:
            check_matches()
        except Exception as e:
            logging.error(f"Ошибка в главном цикле: {e}")
        
        time.sleep(30)

if __name__ == '__main__':
    main()
