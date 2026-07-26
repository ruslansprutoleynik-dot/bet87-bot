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

# Усовершенствованные заголовки для обхода базовых фильтров
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://www.sofascore.com",
    "Referer": "https://www.sofascore.com/",
    "Cache-Control": "no-cache"
}

# Память для уже отправленных сигналов (чтобы не спамить повторно)
sent_signals = set()

# Исключаемые ключевые слова в названиях лиг/категорий
EXCLUDED_KEYWORDS = [
    "women", "жен", "u17", "u18", "u19", "u20", "u21", "u23", 
    "reserve", "резерв", "friendly", "товарищ", "cup", "кубок", "pokal"
]

# --- Мини-сервер для предотвращения сна на Render ---
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
# ----------------------------------------------------

def send_telegram_message(text):
    """Отправка уведомления в Telegram"""
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
        logging.error(f"Ошибка отправки в Telegram: {e}")

def is_valid_league(tournament_name, category_name):
    """Фильтрация лиг (отсеиваем молодежки, кубки, женщин и т.д.)"""
    full_name = f"{category_name} {tournament_name}".lower()
    for kw in EXCLUDED_KEYWORDS:
        if kw in full_name:
            return False
    return True

def check_score_condition(home_score, away_score):
    """Проверка стратегии по счёту: разница 1 гол либо 2:0 / 0:2"""
    try:
        h = int(home_score)
        a = int(away_score)
        diff = abs(h - a)
        if diff == 1:
            return True
        if (h == 2 and a == 0) | (h == 0 and a == 2):
            return True
    except (TypeError, ValueError):
        return False
    return False

def get_match_corners(event_id):
    """Безопасное получение угловых матча (если недоступно — не падаем)"""
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
                                return int(stat.get("home", 0)), int(stat.get("away", 0))
    except Exception:
        pass
    return None, None

def scan_live_matches():
    """Основной цикл сканирования лайва"""
    url = "https://api.sofascore.com/api/v3/events/live"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        
        if response.status_code == 403:
            logging.warning("SofaScore заблокировал запрос (403 Forbidden). Пропуск шага.")
            return
        if response.status_code != 200:
            logging.warning(f"SofaScore вернул код ответа: {response.status_code}")
            return

        data = response.json()
        events = data.get("events", [])

        for event in events:
            if event.get("sport", {}).get("slug") != "football":
                continue

            event_id = event.get("id")
            if not event_id or event_id in sent_signals:
                continue

            # Проверка статуса (только матчи в процессе)
            status = event.get("status", {})
            if status.get("type") != "inprogress":
                continue

            # Минута матча
            minute = event.get("time", {}).get("played")
            if not isinstance(minute, int) or not (80 <= minute <= 87):
                continue

            # Информация о турнире и лиге
            tournament = event.get("tournament", {})
            category = tournament.get("category", {})
            t_name = tournament.get("name", "")
            c_name = category.get("name", "")

            if not is_valid_league(t_name, c_name):
                continue

            # Счет матча
            home_score = event.get("homeScore", {}).get("current")
            away_score = event.get("awayScore", {}).get("current")

            if not check_score_condition(home_score, away_score):
                continue

            # Команды
            home_team = event.get("homeTeam", {}).get("name", "Хозяева")
            away_team = event.get("awayTeam", {}).get("name", "Гости")

            # Угловые (второстепенно)
            h_corners, a_corners = get_match_corners(event_id)
            if h_corners is not None and a_corners is not None:
                corners_str = f"{h_corners + a_corners} ({h_corners} - {a_corners})"
            else:
                corners_str = "Нет данных"

            # Формирование сигнала
            message = (
                f"🔔 <b>СИГНАЛ: ТОТАЛ БОЛЬШЕ (УГЛОВЫЕ)</b>\n\n"
                f"🏆 <b>Лига:</b> {c_name} — {t_name}\n"
                f"⚔️ <b>Матч:</b> {home_team} — {away_team}\n"
                f"⏱ <b>Минута:</b> {minute}'\n"
                f"⚽️ <b>Счёт:</b> {home_score} : {away_score}\n"
                f"🚩 <b>Угловые:</b> {corners_str}\n\n"
                f"⚡️ <i>Лови момент по стратегии!</i>"
            )

            send_telegram_message(message)
            sent_signals.add(event_id)
            logging.info(f"Отправлен сигнал: {home_team} vs {away_team} ({minute}')")

    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка сети при запросе к SofaScore: {e}")
    except Exception as e:
        logging.error(f"Непредвиденная ошибка сканирования: {e}")

if __name__ == "__main__":
    logging.info("Инициализация веб-сервера анти-сна...")
    keep_alive()
    
    logging.info("Бот запущен и готов к работе...")
    send_telegram_message("🚀 <b>Бот успешно перезапущен и полностью готов к работе!</b>")
    
    while True:
        scan_live_matches()
        time.sleep(60)
