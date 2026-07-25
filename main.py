import os
import time
import requests
import logging

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

def send_telegram_message(text):
    """Отправка сообщения в Telegram"""
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

def is_valid_league(tournament_name, category_name):
    """Проверка лиги на фильтры (отсекаем молодёжки, женщин, кубки и т.д.)"""
    full_name = f"{category_name} {tournament_name}".lower()
    for kw in EXCLUDED_KEYWORDS:
        if kw in full_name:
            return False
    return True

def check_score_condition(home_score, away_score):
    """Проверка счёта: разница в 1 мяч или 2:0 / 0:2"""
    diff = abs(home_score - away_score)
    if diff == 1:
        return True
    if (home_score == 2 and away_score == 0) or (home_score == 0 and away_score == 2):
        return True
    return False

def get_match_corners(event_id):
    """Запрос статистики по угловым для конкретного матча"""
    url = f"https://api.sofascore.com/api/v3/event/{event_id}/statistics"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for group in data.get("statistics", []):
                # Берем общую статистику за весь матч (ALL)
                if group.get("period") == "ALL":
                    for item in group.get("groups", []):
                        for stat in item.get("statisticsItems", []):
                            if stat.get("name") == "Corner kicks":
                                home_corners = int(stat.get("home", 0))
                                away_corners = int(stat.get("away", 0))
                                return home_corners, away_corners
    except Exception as e:
        logging.error(f"Ошибка получения статистики угловых для ID {event_id}: {e}")
    return None, None

def scan_live_matches():
    """Сканирование лайв-матчей"""
    url = "https://api.sofascore.com/api/v3/events/live"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
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
            if event_id in sent_signals:
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

            # Минута определяется по времени начала второго тайма или полю minute
            time_info = event.get("time", {})
            minute = time_info.get("played")

            if not minute or not (80 <= minute <= 87):
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
            corners_str = f"{home_corners + away_corners} ({home_corners} - {away_corners})" if home_corners is not None else "Нет данных"

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

    except Exception as e:
        logging.error(f"Ошибка при сканировании: {e}")

if __name__ == "__main__":
    logging.info("Бот-сканер успешно запущен...")
    # Оповещение в Telegram о старте
    send_telegram_message("🚀 <b>Бот-сканер 87 запущен и сканирует лайв-матчи!</b>")
    
    while True:
        scan_live_matches()
        time.sleep(60)  # Сканируем каждую минуту
