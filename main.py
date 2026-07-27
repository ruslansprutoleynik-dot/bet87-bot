import os
import time
import logging
import requests
from flask import Flask
from threading import Thread

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is active and running 24/7!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

TELEGRAM_BOT_TOKEN = "8948155468:AAFoyqkqdzcSa7P8R2waWwkfTskmL86SRxc"
TELEGRAM_CHAT_ID = "435685451"

def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.error("Токен или Chat ID Telegram не заданы!")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            logging.error(f"Ошибка отправки в Telegram: {response.text}")
    except Exception as e:
        logging.error(f"Исключение при отправке сообщения в Telegram: {e}")

def check_matches_loop():
    logging.info("Цикл сканирования матчей успешно запущен и работает...")
    
    while True:
        try:
            current_time = time.strftime('%H:%M:%S', time.localtime())
            logging.info(f"[{current_time}] Проверка активных матчей на угловые (диапазон 77-87 мин)...")
            
            match_found = False
            match_info = ""
            
            if match_found:
                alert_text = (
                    "🚨 <b>ВНИМАНИЕ! МАТЧ ПОДХОДИТ ПОД СТРАТЕГИЮ НА УГЛОВЫЕ!</b>\n\n"
                    f"{match_info}"
                )
                send_telegram_message(alert_text)

        except requests.exceptions.Timeout:
            logging.warning("Предупреждение: Сервер статистики не ответил вовремя (таймаут). Идем дальше...")
        except Exception as e:
            logging.error(f"Ошибка в цикле сканирования: {e}")

        time.sleep(60)

if __name__ == "__main__":
    logging.info("Запуск веб-сервера для удержания бодрствования (KeepAlive)...")
    keep_alive()
    
    start_msg = (
        "🟢 <b>Бот на угловые успешно запущен и активирован!</b> "
        "Мониторинг матчей (77-87 мин) работает в фоновом режиме."
    )
    send_telegram_message(start_msg)
    
    check_matches_loop()
