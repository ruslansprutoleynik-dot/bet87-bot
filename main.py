import os
import time
import logging
import requests
from flask import Flask
from threading import Thread

# ====================== НАСТРОЙКИ ======================
TELEGRAM_BOT_TOKEN = "8948155468:AAFoyqkqdzcSa7P8R2waWwkfTskmL86SRxc"
TELEGRAM_CHAT_ID = "435685451"
FOOTBALL_DATA_TOKEN = "dc8ff1e7f71644119a005fab09e4964c"

MIN_MINUTE = 77
MAX_MINUTE = 87
CHECK_INTERVAL = 30

BLACKLIST_KEYWORDS = [
    "women", "woman", "female", "w ", " w/",
    "u19", "u20", "u21", "u23", "youth", "junior", "reserve", "reserves",
    "friendly", "friendlies", "cup", "copa", "coupe", "pokal", "trophy",
    "qualification", "qualifiers", "play-off", "playoff"
]

ALLOWED_SCORES = {
    (1, 0), (0, 1),
    (2, 0), (0, 2),
    (2, 1), (1, 2),
    (3, 2), (2, 3),
    (4, 3), (3, 4),
    (5, 4), (4, 5),
    (6, 5), (5, 6),
    (7, 6), (6, 7),
}
# =======================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
sent_matches = set()

@app.route('/')
def home():
    return "Corners Bot is alive and monitoring!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask, daemon=True)
    t.start()

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            logger.error(f"Telegram error: {r.text}")
    except Exception as e:
        logger.error(f"Telegram exception: {e}")

def is_blacklisted(competition_name: str) -> bool:
    name = competition_name.lower()
    return any(kw in name for kw in BLACKLIST_KEYWORDS)

def is_allowed_score(home: int, away: int) -> bool:
    return (home, away) in ALLOWED_SCORES

def get_live_matches():
    url = "https://api.football-data.org/v4/matches"
    headers = {"X-Auth-Token": FOOTBALL_DATA_TOKEN}
    params = {"status": "IN_PLAY,PAUSED"}

    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        if r.status_code != 200:
            logger.warning(f"API status {r.status_code}: {r.text[:200]}")
            return []
        data = r.json()
        return data.get("matches", [])
    except Exception as e:
        logger.error(f"Ошибка запроса к API: {e}")
        return []

def check_matches():
    matches = get_live_matches()
    logger.info(f"Найдено live-матчей: {len(matches)}")

    for match in matches:
        try:
            match_id = match["id"]
            if match_id in sent_matches:
                continue

            minute = match.get("minute")
            if minute is None:
                continue
            try:
                minute = int(minute)
            except:
                continue

            if not (MIN_MINUTE <= minute <= MAX_MINUTE):
                continue

            score = match.get("score", {}).get("fullTime", {})
            home_score = score.get("home")
            away_score = score.get("away")

            if home_score is None or away_score is None:
                continue

            if not is_allowed_score(home_score, away_score):
                continue

            competition = match.get("competition", {})
            comp_name = competition.get("name", "Unknown")
            if is_blacklisted(comp_name):
                continue

            home_team = match["homeTeam"]["name"]
            away_team = match["awayTeam"]["name"]

            msg = (
                f"🚨 <b>СИГНАЛ НА УГЛОВЫЕ!</b>\n\n"
                f"⚽ <b>{home_team}</b> {home_score}:{away_score} <b>{away_team}</b>\n"
                f"⏱ Минута: <b>{minute}'</b>\n"
                f"🏆 Лига: {comp_name}\n\n"
                f"💰 Можно ставить тотал угловых больше 0.5 от текущего"
            )

            send_telegram(msg)
            sent_matches.add(match_id)
            logger.info(f"СИГНАЛ ОТПРАВЛЕН: {home_team} {home_score}:{away_score} {away_team} ({minute}')")

        except Exception as e:
            logger.error(f"Ошибка обработки матча: {e}")

def main_loop():
    logger.info("Цикл мониторинга запущен")
    while True:
        try:
            check_matches()
        except Exception as e:
            logger.error(f"Ошибка в главном цикле: {e}")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    logger.info("Запуск бота...")
    keep_alive()

    start_msg = (
        "🟢 <b>Бот на угловые запущен!</b>\n"
        f"Мониторинг матчей {MIN_MINUTE}–{MAX_MINUTE} минута\n"
        "Нужные счета: разница 1 гол + 2-0 / 0-2"
    )
    send_telegram(start_msg)

    main_loop()
