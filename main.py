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

sent_signals = set()

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
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.error("КРИТИЧЕСКАЯ ОШИБКА: Не заданы TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID в переменных окружения Render!")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logging.info("Сообщение в Telegram успешно отправлено.")
            return True
        else:
            logging.error(f"Telegram вернул ошибку: {response.text}")
            return False
    except Exception as e:
        logging.error(f"Ошибка отправки в Telegram: {e}")
        return False

def is_valid_league(league_name):
    l_lower = league_name.lower()
    for kw in EXCLUDED_KEYWORDS:
        if kw in l_lower:
            return False
    return True

def check_score_condition(home_score, away_score):
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
    url = "https://raw.githubusercontent.com/openfootball/football.json/master/2025-26/en.1.json"
    logging.info("Начало цикла проверки матчей...")
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            logging.warning(f"GitHub отдал код ответа: {response.status_code}")
            return

        if not response.text or len(response.text.strip()) == 0:
            logging.warning("Пустой ответ от источника данных.")
            return

        data = response.json()
        matches = data.get("matches", [])
        logging.info(f"Получено матчей для анализа: {len(matches)}")

        for match in matches:
            match_id = str(match.get("date")) + str(match.get("team1"))
            if match_id in sent_signals:
                continue

            score = match.get("score", {})
            ft = score.get("ft")
            if not ft or len(ft) != 2:
                continue

            home_score, away_score = ft[0], ft[1]
            home_team = match.get("team1", {}).get("name", "Хозяева")
            away_team = match.get("team2", {}).get("name", "Гости")
            league = data.get("name", "Premier League")

            if not is_valid_league(league):
                continue

            if not check_score_condition(home_score, away_score):
                continue

            message = (
                f"🔔 <b>СИГНАЛ ПО СТРАТЕГИИ (УГЛОВЫЕ)</b>\n\n"
                f"🏆 <b>Лига:</b> {league}\n"
                f"⚔️ <b>Матч:</b> {home_team} — {away_team}\n"
                f"⚽️ <b>Счёт:</b> {home_score} : {away_score}\n\n"
                f"⚡️ <i>Момент по стратегии!</i>"
            )

            send_telegram_message(message)
            sent_signals.add(match_id)
            logging.info(f"Отправлен сигнал для матча: {home_team} vs {away_team}")

    except Exception as e:
        logging.error(f"Ошибка во время сканирования матчей: {e}")

if __name__ == "__main__":
    logging.info("Инициализация веб-сервера Keep-Alive...")
    keep_alive()
    
    logging.info("Бот запущен. Пробуем отправить стартовое сообщение в Telegram...")
    
    # Жесткая проверка связи со стартовым уведомлением
    startup_success = send_telegram_message("🚀 <b>Бот успешно запущен, переподключен и начал работу!</b>")
    if startup_success:
        logging.info("Стартовое сообщение успешно доставлено в чат.")
    else:
        logging.error("ВНИМАНИЕ: Стартовое сообщение НЕ ушло! Проверь TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID в настройках Render.")
    
    while True:
        scan_live_matches()
        logging.info("Пауза цикла 60 секунд...")
        time.sleep(60)
