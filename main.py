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

# Память для уже отправленных сигналов
sent_signals = set()

# Исключаемые ключевые слова
EXCLUDED_KEYWORDS = [
    "women", "жен", "u17", "u18", "u19", "u20", "u21", "u23", 
    "reserve", "резерв", "friendly", "товарищ", "cup", "кубок", "pokal", "amateur"
]

# --- Мини-сервер против сна на Render ---
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is active!")
    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), KeepAliveHandler)
    server.serve_forever()

def keep_alive():
    t = Thread(target=run_server, daemon=True)
    t.start()
# ----------------------------------------

def send_telegram_message(text):
    """Отправка уведомления в Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.error("Не заданы токены Telegram!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Ошибка отправки в Telegram: {e}")

def is_valid_league(league_name):
    """Фильтрация лиг"""
    l_lower = league_name.lower()
    for kw in EXCLUDED_KEYWORDS:
        if kw in l_lower:
            return False
    return True

def check_score_condition(home_score, away_score):
    """Проверка стратегии по счёту"""
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
    """Сканирование матчей"""
    url = "https://www.thesportsdb.com/api/v1/json/3/eventsday.php?s=Soccer"
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            logging.warning("Сервер данных временно недоступен.")
            return

        data = response.json()
        events = data.get("events") or []

        for event in events:
            event_id = event.get("idEvent")
            if not event_id or event_id in sent_signals:
                continue

            progress = event.get("strProgress")
            if not progress:
                continue

            minute_str = "".join(filter(str.isdigit, progress))
            if not minute_str:
                continue
            
            minute = int(minute_str)
            if not (80 <= minute <= 87):
                continue

            league = event.get("strLeague", "Неизвестная лига")
            if not is_valid_league(league):
                continue

            home_team = event.get("strHomeTeam", "Хозяева")
            away_team = event.get("strAwayTeam", "Гости")
            
            home_score = event.get("intHomeScore")
            away_score = event.get("intAwayScore")

            if home_score is None or away_score is None:
                continue

            if not check_score_condition(home_score, away_score):
                continue

            message = (
                f"🔔 <b>СИГНАЛ ПО СТРАТЕГИИ (УГЛОВЫЕ)</b>\n\n"
                f"🏆 <b>Лига:</b> {league}\n"
                f"⚔️ <b>Матч:</b> {home_team} — {away_team}\n"
                f"⏱ <b>Минута:</b> {minute}'\n"
                f"⚽️ <b>Текущий счёт:</b> {home_score} : {away_score}\n\n"
                f"⚡️ <i>Включай трансляцию, лови момент!</i>"
            )

            send_telegram_message(message)
            sent_signals.add(event_id)
            logging.info(f"Отправлен сигнал: {home_team} vs {away_team} ({minute}')")

    except Exception as e:
        logging.error(f"Ошибка в цикле сканирования: {e}")

if __name__ == "__main__":
    logging.info("Инициализация веб-сервера...")
    keep_alive()
    
    logging.info("Бот запущен и работает стабильно...")
    send_telegram_message("🚀 <b>Бот успешно обновлен и запущен в штатном режиме!</b>")
    
    while True:
        scan_live_matches()
        time.sleep(60)
