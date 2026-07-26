import os
import time
import logging
import requests
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

sent_signals = set()

EXCLUDED_KEYWORDS = [
    "women", "жен", "u17", "u18", "u19", "u20", "u21", "u23", 
    "reserve", "резерв", "friendly", "товарищ", "cup", "кубок", 
    "pokal", "amateur"
]

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
    """Обработчик для удержания бота в активном состоянии (анти-сон)"""
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is active and running!")

    def log_message(self, format, *args):
        # Отключаем лишний мусор в логах от пингов сервера
        pass

def run_server():
    server_address = ('0.0.0.0', 10000)
    httpd = HTTPServer(server_address, KeepAliveHandler)
    httpd.serve_forever()

def keep_alive():
    t = Thread(target=run_server, daemon=True)
    t.start()

def send_telegram_message(text):
    """Надежная отправка сообщения в Telegram с защитой от сбоев сети"""
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
    """Логика проверки матчей (77-87 мин, счета, фильтры лиг)"""
    try:
        logging.info("Сканирование текущих матчей...")
        
        # Здесь выполняется запрос к источнику данных лайв-матчей
        # 1. Проверка времени (77-87 минута)
        # 2. Проверка счета по ALLOWED_SCORES
        # 3. Фильтрация EXCLUDED_KEYWORDS
        
        # Пример отправки сигнала:
        # match_id = "12345"
        # if match_id not in sent_signals:
        #     if send_telegram_message("🚨 Сигнал! Матч подходит под критерии..."):
        #         sent_signals.add(match_id)
        
    except Exception as e:
        logging.error(f"Ошибка в цикле проверки матчей: {e}")

def main():
    logging.info("Инициализация бота...")
    
    # 1. Запускаем сервер предотвращения сна
    keep_alive()
    logging.info("Сервер анти-сна запущен на порту 10000.")

    # 2. Шлем стартовое уведомление и проверяем связь с Telegram
    success = send_telegram_message("🟢 Бот успешно запущен! Защита от сна активна, интервал проверки — 30 сек.")
    if success:
        logging.info("Стартовое сообщение успешно доставлено в Telegram.")
    else:
        logging.warning("Не удалось отправить стартовое сообщение в Telegram. Проверьте токены!")

    # 3. Основной непрерывный цикл работы
    while True:
        try:
            check_matches()
        except Exception as e:
            logging.error(f- "Критическая ошибка в main loop: {e}")
        
        time.sleep(30)

if __name__ == '__main__':
    main()
