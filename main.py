import os
import time
import logging
import requests
from flask import Flask
from threading import Thread

# Настройка логов для панели Render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask('')

@app.route('/')
def home():
    return "Bot is active and running 24/7!"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# Получаем настройки из переменных окружения Render
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.error("Токен или Chat ID Telegram не заданы в переменных окружения!")
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
            # Это пишется ТОЛЬКО в логи на Render, в Telegram это НЕ летит, чтобы не спамить
            logging.info(f"[{current_time}] Проверка активных матчей (диапазон 77-87 мин)...")
            
            # ==========================================
            # ТУТ ВАШ КОД ПРОВЕРКИ МАТЧЕЙ И СТАТИСТИКИ
            # ==========================================
            match_found = False  # Пример флага
            match_info = ""      # Пример текста о матче
            
            # Если бот нашел подходящий матч под стратегию:
            if match_found:
                # ТОЛЬКО ТУТ отправляем уведомление в Telegram со звуком
                alert_text = f"🚨 <b>ВНИМАНИЕ! МАТЧ ПОДХОДИТ ПОД СТРАТЕГИЮ!</b>\n\n{match_info}"
                send_telegram_message(alert_text)

        except requests.exceptions.Timeout:
            logging.warning("Предупреждение: Сервер статистики не ответил вовремя (таймаут). Идем дальше...")
        except Exception as e:
            logging.error(f"Ошибка в цикле сканирования: {e}")

        # Пауза 60 секунд перед следующей проверкой
        time.sleep(60)

if __name__ == "__main__":
    logging.info("Запуск веб-сервера для удержания бодрствования (KeepAlive)...")
    keep_alive()
    
    # Приветствие отправляется в Telegram ОДИН РАЗ при старте бота
    send_telegram_message("🟢 <b>Бот успешно запущен и активирован!</b> Мониторинг матчей (77-87 мин) запущен в фоновом режиме. Ожидаем подходящие матчи...")
    
    # Запускаем бесконечный цикл проверки
    check_matches_loop()
