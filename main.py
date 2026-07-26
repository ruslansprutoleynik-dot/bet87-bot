import os
import time
import requests
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Переменные окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Память для уже отправленных сигналов (чтобы не слать дубликаты)
sent_signals = set()

# Исключаемые ключевые слова (молодежки, женщины, товарищеские матчи)
EXCLUDED_KEYWORDS = [
    "women", "жен", "u17", "u18", "u19", "u20", "u21", "u23", 
    "reserve", "резерв", "friendly", "товарищ", "cup", "кубок", "pokal", "amateur"
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
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), KeepAliveHandler)
    server.serve_forever()

def keep_alive():
    t = Thread(target=run_server, daemon=True)
    t.start()
# -----------------------------------------------------------------------

def send_telegram_message(text):
    """Отправка уведомления в Telegram-канал или чат"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.error("Не заданы TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logging.error(f"Ошибка отправки сообщения в Telegram: {e}")

def is_valid_league(league_name):
    """Фильтрация лиг по стоп-словам"""
    l_lower = league_name.lower()
    for kw in EXCLUDED_KEYWORDS:
        if kw in l_lower:
            return False
    return True

def check_score_condition(home_score, away_score):
    """Стратегия: разница в 1 гол либо счета 2:0 / 0:2"""
    try:
        h = int(home_score)
        a = int(away_score)
        diff = abs(h - a)
        if diff == 1:
            return True
        if (h == 2 and a == 0) or (h == 0 and a == 2):
            return True
    except (TypeError, ValueError):
        return False
    return False

def scan_live_matches():
    """Основной сканер матчей через надежный публичный спортивный поток"""
    # Используем стабильный эндпоинт открытых спортивных данных
    url = "https://www.the
