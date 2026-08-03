# ====================================
# UNIVERSAL SPORTS MONITOR
# Full version with Telegram control
# ====================================

import os
import time
import logging
import requests
from flask import Flask
from threading import Thread

# ---------- TELEGRAM ----------
TELEGRAM_BOT_TOKEN = "8948155468:AAFoyqkqdzcSa7P8R2waWwkfTskmL86SRxc"
TELEGRAM_CHAT_ID = "435685451"

# ---------- FOOTBALL API ----------
FOOTBALL_DATA_TOKEN = "dc8ff1e7f71644119a005fab09e4964c"

# ---------- SERVER ----------
BOT_URL = "https://bet87-bot.onrender.com"

# ---------- SETTINGS ----------
CHECK_INTERVAL = 30
PING_INTERVAL = 240
REQUEST_TIMEOUT = 15
MIN_MINUTE = 77
MAX_MINUTE = 87

# ---------- TOP COMPETITIONS ----------
TOP_COMPETITIONS = {
    "Premier League",
    "La Liga",
    "Serie A",
    "Bundesliga",
    "Ligue 1",
    "Primeira Liga",
    "Eredivisie",
    "UEFA Champions League",
    "UEFA Europa League",
    "UEFA Conference League",
    "FIFA World Cup",
    "European Championship"
}

# ---------- BLACKLIST ----------
BLACKLIST = [
    "women", "woman", "female",
    "u17", "u18", "u19", "u20", "u21", "u23",
    "reserve", "reserves",
    "friendly", "friendlies",
    "cup", "copa", "coupe", "pokal",
    "qualification", "qualifier",
    "playoff", "play-off"
]

# ---------- STATE ----------
class ServiceState:
    def __init__(self):
        self.running = True

    def pause(self):
        self.running = False

    def resume(self):
        self.running = True

    def status(self):
        return "RUNNING" if self.running else "PAUSED"

state = ServiceState()
sent_matches = set()
last_ping = 0
last_update_id = 0

# ---------- LOGGING ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("SPORTS_MONITOR")

# ---------- FLASK ----------
app = Flask(__name__)

@app.route("/")
def home():
    return "Universal Sports Monitor is alive", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

def keep_alive():
    Thread(target=run_flask, daemon=True).start()

# ---------- TELEGRAM ----------
def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code != 200:
            logger.error(f"Telegram error: {r.text}")
    except Exception as e:
        logger.exception(e)

def self_ping():
    global last_ping
    now = time.time()
    if now - last_ping < PING_INTERVAL:
        return
    try:
        requests.get(BOT_URL, timeout=10)
        last_ping = now
        logger.info("Self-ping OK")
    except Exception as e:
        logger.warning(f"Self-ping failed: {e}")

# ---------- COMMANDS ----------
def process_commands():
    global last_update_id
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {
        "offset": last_update_id + 1,
        "timeout": 1
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return
        data = r.json()
        for update in data.get("result", []):
            last_update_id = update["update_id"]
            message = update.get("message", {})
            text = message.get("text", "").strip().lower()
            chat_id = str(message.get("chat", {}).get("id", ""))

            if chat_id != TELEGRAM_CHAT_ID:
                continue

            if text in ["/start", "/run", "старт", "запуск"]:
                state.resume()
                send_telegram("🟢 Мониторинг <b>включён</b>")
                logger.info("Service RESUMED by command")

            elif text in ["/stop", "/pause", "стоп", "пауза"]:
                state.pause()
                send_telegram("🔴 Мониторинг <b>остановлен</b>")
                logger.info("Service PAUSED by command")

            elif text in ["/status", "статус"]:
                status = state.status()
                send_telegram(f"📊 Статус: <b>{status}</b>")

    except Exception as e:
        logger.exception(e)

def commands_loop():
    while True:
        process_commands()
        time.sleep(3)

# ---------- API + FILTERS ----------
def get_live_matches():
    url = "https://api.football-data.org/v4/matches"
    headers = {"X-Auth-Token": FOOTBALL_DATA_TOKEN}
    params = {"status": "IN_PLAY,PAUSED"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            logger.warning(f"API status: {r.status_code}")
            return []
        return r.json().get("matches", [])
    except Exception as e:
        logger.exception(e)
        return []

def is_blacklisted(name):
    if not name:
        return True
    lower = name.lower()
    return any(word in lower for word in BLACKLIST)

def is_top_competition(name):
    return name in TOP_COMPETITIONS if name else False

def check_matches():
    matches = get_live_matches()
    logger.info(f"Live matches: {len(matches)}")

    for match in matches:
        try:
            match_id = match.get("id")
            if not match_id or match_id in sent_matches:
                continue

            minute = match.get("minute")
            if minute is None:
                continue
            minute = int(minute)

            if not (MIN_MINUTE <= minute <= MAX_MINUTE):
                continue

            competition = match.get("competition", {})
            comp_name = competition.get("name", "")

            if is_blacklisted(comp_name) or not is_top_competition(comp_name):
                continue

            score = match.get("score", {}).get("fullTime", {})
            home_score = score.get("home")
            away_score = score.get("away")

            if home_score is None or away_score is None:
                continue

            if abs(home_score - away_score) != 1:
                continue

            home_team = match["homeTeam"]["name"]
            away_team = match["awayTeam"]["name"]

            msg = (
                f"⚽ <b>СИГНАЛ НА УГЛОВЫЕ</b>\n\n"
                f"🏆 {comp_name}\n"
                f"⚔️ <b>{home_team}</b> {home_score}:{away_score} <b>{away_team}</b>\n"
                f"⏱ Минута: <b>{minute}'</b>\n\n"
                f"💰 Можно ставить тотал угловых больше 0.5"
            )

            send_telegram(msg)
            sent_matches.add(match_id)
            logger.info(f"[SIGNAL] {home_team} {home_score}:{away_score} {away_team} | {minute}' | {comp_name}")

        except Exception as e:
            logger.exception(e)

# ---------- MAIN ----------
def main():
    logger.info("Starting Universal Sports Monitor...")
    keep_alive()
    time.sleep(2)

    Thread(target=commands_loop, daemon=True).start()

    send_telegram(
        "🟢 <b>Бот запущен</b>\n\n"
        "Команды:\n"
        "/start — включить мониторинг\n"
        "/stop — остановить\n"
        "/status — статус"
    )

    while True:
        try:
            process_commands()
            if state.running:
                check_matches()
                self_ping()
        except Exception as e:
            logger.exception(e)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
