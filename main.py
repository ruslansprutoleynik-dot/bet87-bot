import os
import time
import requests
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Токен бота и ID чата берутся из переменных окружения (Render)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Заголовки для имитации браузера при запросах к SofaScore
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Referer": "https://www.sofascore.com/"
}

# Множество для хранения ID матчей, по которым уже отправлен сигнал
sent_signals = set()

# Слова-маркеры для исключения ненужных матчей
EXCLUDED_KEYWORDS = [
    "women", "жен", "u17", "u18", "u19", "u20", "u21", "u23", 
    "reserve", "резерв", "friendly", "товарищ", "cup", "кубок", "pokal"
]

# --- HTTP Сервер для защиты от сна на Render (Anti-Sleep) ---
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")
        
    def log_message(self, format, *args):
        pass # Отключаем спам в логах, когда сервер проверяют на "сон"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), KeepAliveHandler)
    server.serve_forever()

def keep_alive():
    t = Thread(target=run_server)
    t.daemon = True
    t.start()
# -----------------------------------------------------------

def send_telegram_message(text):
    """Отправка сообщения в Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status() # Проверка успешности отправки
    except Exception as e:
        logging.error(f"Ошибка отправки в Telegram: {e}")

def is_valid_league(tournament_name, category_name):
    """Проверка лиги на фильтры (отсекаем молодёжки, женщин, кубки и т.д.)"""
    full_name = f"{category_name} {tournament_name}".lower()
    for kw in EXCLUDED_KEYWORDS:
        if kw in full_name:
            return False
    return True

def check_score_condition(home_score, away_score):
    """Проверка счёта: разница в 1 мяч или 2:0 / 0:2"""
    try:
        home_score = int(home_score)
        away_score = int(away_score)
        diff = abs(home_score - away_score)
        if diff == 1:
            return True
        if (home_score == 2 and away_score == 0) or (home_score == 0 and away_score == 2):
            return True
    except (TypeError, ValueError):
        return False # Если счет пришел кривой, игнорируем матч
    return False

def get_match_corners(event_id):
    """Запрос статистики по угловым для конкретного матча"""
    url = f"https://api.sofascore.com/api/v3/event/{event_id}/statistics"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for group in data.get("statistics", []):
                if group.get("period") == "ALL":
                    for item in group.get("groups", []):
                        for stat in item.get("statisticsItems", []):
                            if stat.get("name") == "Corner kicks":
                                home_corners = int(stat.get("home", 0))
                                away_corners = int(stat.get("away", 0))
                                return home_corners, away_corners
    except Exception as e:
        logging.error(f"Сбой получения угловых (ID {event_id}): {e}. Идем без них.")
    return None, None

def scan_live_matches():
    """Сканирование лайв-матчей"""
    url = "https://api.sofascore.com/api/v3/events/live"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            logging.warning(f"SofaScore вернул статус {response.status_code}")
            return

        data = response.json()
        events = data.get("events", [])

        for event in events:
            # Проверяем только футбол
            if event.get("sport", {}).get("slug") != "football":
                continue

            event_id = event.get("id")
            if not event_id or event_id in sent_signals:
                continue

            # Получаем информацию о лиге
            tournament = event.get("tournament", {})
            category = tournament.get("category", {})
            tournament_name = tournament.get("name", "")
            category_name = category.get("name", "")

            # Фильтр лиг
            if not is_valid_league(tournament_name, category_name):
                continue

            # Проверка времени (минуты)
            status = event.get("status", {})
            if status.get("type") != "inprogress":
                continue

            time_info = event.get("time", {})
            minute = time_info.get("played")

            if not minute or not isinstance(minute, int) or not (80 <= minute <= 87):
                continue

            # Проверка счёта
            home_score = event.get("homeScore", {}).get("current")
            away_score = event.get("awayScore", {}).get("current")

            if home_score is None or away_score is None:
                continue

            if not check_score_condition(home_score, away_score):
                continue

            # Если всё совпало — запрашиваем угловые
            home_team = event.get("homeTeam", {}).get("name", "Хозяева")
            away_team = event.get("awayTeam", {}).get("name", "Гости")
            
            home_corners, away_corners = get_match_corners(event_id)
            corners_str = f"{home_corners + away_corners} ({home_corners} - {away_corners})" if home_corners is not None else "Нет данных (SofaScore не дал стату)"

            # Формируем сообщение
            message = (
                f"🔔 <b>СИГНАЛ: ТОТАЛ БОЛЬШЕ (УГЛОВЫЕ)</b>\n\n"
                f"🏆 <b>Лига:</b> {category_name} — {tournament_name}\n"
                f"⚔️ <b>Матч:</b> {home_team} — {away_team}\n"
                f"⏱ <b>Минута:</b> {minute}'\n"
                f"⚽️ <b>Счёт:</b> {home_score} : {away_score}\n"
                f"🚩 <b>Угловые:</b> {corners_str}\n\n"
                f"⚡️ <i>Готовься ловить ТБ по угловым!</i>"
            )

            send_telegram_message(message)
            sent_signals.add(event_id)
            logging.info(f"Отправлен сигнал по матчу: {home_team} vs {away_team}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка соединения с SofaScore: {e}")
    except Exception as e:
        logging.error(f"Непредвиденная ошибка в основном цикле: {e}")

if __name__ == "__main__":
    logging.info("Запуск фонового веб-сервера для Render...")
    keep_alive()  # Запускаем сервер, чтобы Render не убил бота
    
    logging.info("Бот-сканер успешно запущен...")
    send_telegram_message("🚀 <b>Бот-сканер 87 запущен и сканирует лайв-матчи! Анти-сон активирован.</b>")
    
    while True:
        try:
            scan_live_matches()
        except Exception as e:
            logging.error(f"Сбой в бесконечном цикле: {e}")
        
        time.sleep(60)  # Сканируем каждую минуту
