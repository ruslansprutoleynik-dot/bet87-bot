# =====================================================================
# UNIVERSAL SPORTS MONITOR (FOOTBALL + HOCKEY)
# Точные токены со скриншота BotFather
# =====================================================================

import os
import time
import logging
import requests
from flask import Flask
from threading import Thread

# ---------- CREDENTIALS & TOKENS ----------
FOOTBALL_BOT_TOKEN = "8948155468:AAEH8qQndyRRf0WYpENs3pfaot39wNaoEKc"
FOOTBALL_DATA_TOKEN = "dc8ff1e7f71644119a005fab09e4964c"

# Вставлен новый рабочий токен хоккея, проверенный через getMe!
HOCKEY_BOT_TOKEN = "8965841999:AAGBOg32o6gfR1npXyoR3WkPQWUpW-PUmDM"
API_SPORTS_KEY = "c524baddeef5bcc8f56c301063b30ac5"

TELEGRAM_CHAT_ID = "435685451"
BOT_URL = "https://bet87-bot.onrender.com"
REQUEST_TIMEOUT = 15

# ---------- FOOTBALL SETTINGS ----------
FOOTBALL_CHECK_INTERVAL = 30
PING_INTERVAL = 240
MIN_MINUTE = 77
MAX_MINUTE = 87

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

FOOTBALL_BLACKLIST = [
    "women", "woman", "female",
    "u17", "u18", "u19", "u20", "u21", "u23",
    "reserve", "reserves",
    "friendly", "friendlies",
    "cup", "copa", "coupe", "pokal",
    "qualification", "qualifier",
    "playoff", "play-off"
]

# ---------- HOCKEY SETTINGS ----------
HOCKEY_CHECK_INTERVAL = 270

# ---------- STATES ----------
class ServiceState:
    def __init__(self):
        self.running = True

    def pause(self):
        self.running = False

    def resume(self):
        self.running = True

    def status(self):
        return "RUNNING" if self.running else "PAUSED"

football_state = ServiceState()
hockey_state = ServiceState()

sent_football_matches = set()
sent_hockey_matches = set()

last_ping = 0
football_update_id = 0
hockey_update_id = 0

# ---------- LOGGING ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("UNIVERSAL_MONITOR")

# ---------- FLASK (KEEP ALIVE) ----------
app = Flask(__name__)

@app.route("/")
def home():
    return "Universal Sports Monitor Final Tokens is alive", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

def keep_alive():
    Thread(target=run_flask, daemon=True).start()

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

# ---------- TELEGRAM HELPERS ----------
def send_telegram(bot_token, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
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

# ---------- COMMANDS PROCESSORS ----------
def process_football_commands():
    global football_update_id
    url = f"https://api.telegram.org/bot{FOOTBALL_BOT_TOKEN}/getUpdates"
    params = {"offset": football_update_id + 1, "timeout": 1}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return
        data = r.json()
        for update in data.get("result", []):
            football_update_id = update["update_id"]
            message = update.get("message", {})
            text = message.get("text", "").strip().lower()
            chat_id = str(message.get("chat", {}).get("id", ""))

            if chat_id != TELEGRAM_CHAT_ID:
                continue

            if text in ["/start", "/run", "старт", "запуск"]:
                football_state.resume()
                send_telegram(FOOTBALL_BOT_TOKEN, "🟢 Футбольный мониторинг <b>включён</b>")
            elif text in ["/stop", "/pause", "стоп", "пауза"]:
                football_state.pause()
                send_telegram(FOOTBALL_BOT_TOKEN, "🔴 Футбольный мониторинг <b>остановлен</b>")
            elif text in ["/status", "статус"]:
                send_telegram(FOOTBALL_BOT_TOKEN, f"📊 Статус футбола: <b>{football_state.status()}</b>")
    except Exception as e:
        logger.exception(e)

def process_hockey_commands():
    global hockey_update_id
    url = f"https://api.telegram.org/bot{HOCKEY_BOT_TOKEN}/getUpdates"
    params = {"offset": hockey_update_id + 1, "timeout": 1}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return
        data = r.json()
        for update in data.get("result", []):
            hockey_update_id = update["update_id"]
            message = update.get("message", {})
            text = message.get("text", "").strip().lower()
            chat_id = str(message.get("chat", {}).get("id", ""))

            if chat_id != TELEGRAM_CHAT_ID:
                continue

            if text in ["/start", "/run", "старт", "запуск"]:
                hockey_state.resume()
                send_telegram(HOCKEY_BOT_TOKEN, "🟢 Хоккейный мониторинг <b>включён</b>")
            elif text in ["/stop", "/pause", "стоп", "пауза"]:
                hockey_state.pause()
                send_telegram(HOCKEY_BOT_TOKEN, "🔴 Хоккейный мониторинг <b>остановлен</b>")
            elif text in ["/status", "статус"]:
                send_telegram(HOCKEY_BOT_TOKEN, f"📊 Статус хоккея: <b>{hockey_state.status()}</b>")
    except Exception as e:
        logger.exception(e)

def football_commands_loop():
    while True:
        process_football_commands()
        time.sleep(3)

def hockey_commands_loop():
    while True:
        process_hockey_commands()
        time.sleep(3)

# ---------- FOOTBALL LOGIC ----------
def get_live_football_matches():
    url = "https://api.football-data.org/v4/matches"
    headers = {"X-Auth-Token": FOOTBALL_DATA_TOKEN}
    params = {"status": "IN_PLAY,PAUSED"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            logger.warning(f"Football API status: {r.status_code}")
            return []
        return r.json().get("matches", [])
    except Exception as e:
        logger.exception(e)
        return []

def check_football():
    matches = get_live_football_matches()
    logger.info(f"Football live matches: {len(matches)}")

    for match in matches:
        try:
            match_id = match.get("id")
            if not match_id or match_id in sent_football_matches:
                continue

            minute = match.get("minute")
            if minute is None:
                continue
            minute = int(minute)

            if not (MIN_MINUTE <= minute <= MAX_MINUTE):
                continue

            competition = match.get("competition", {})
            comp_name = competition.get("name", "")

            if not comp_name:
                continue
            
            lower_comp = comp_name.lower()
            if any(w in lower_comp for w in FOOTBALL_BLACKLIST):
                continue
            if comp_name not in TOP_COMPETITIONS:
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

            send_telegram(FOOTBALL_BOT_TOKEN, msg)
            sent_football_matches.add(match_id)
            logger.info(f"[FOOTBALL SIGNAL] {home_team} {home_score}:{away_score} {away_team} | {minute}'")

        except Exception as e:
            logger.exception(e)

# ---------- HOCKEY LOGIC ----------
def is_women_hockey(league_name):
    name = (league_name or "").lower()
    return any(w in name for w in ["women", "woman", "female", "женск", "женщин"])

def get_live_hockey_games():
    url = "https://v1.hockey.api-sports.io/games"
    headers = {"x-apisports-key": API_SPORTS_KEY}
    params = {"live": "all"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            logger.warning(f"Hockey API status: {r.status_code}")
            return []
        return r.json().get("response", [])
    except Exception as e:
        logger.exception(e)
        return []

def check_hockey():
    games = get_live_hockey_games()
    logger.info(f"Hockey live matches: {len(games)}")

    for game in games:
        try:
            game_id = game.get("id")
            if not game_id or game_id in sent_hockey_matches:
                continue

            league = game.get("league", {}) or {}
            league_name = league.get("name", "Hockey")

            if is_women_hockey(league_name):
                continue

            status = game.get("status", {}) or {}
            short_status = status.get("short", "")
            long_status = (status.get("long") or "").lower()

            if short_status not in ["P2", "2P", "2"] and "2nd" not in long_status and "period 2" not in long_status:
                continue

            scores = game.get("scores", {}) or {}
            home_scores = scores.get("home") or {}
            away_scores = scores.get("away") or {}

            p1_home = home_scores.get("period_1")
            p1_away = away_scores.get("period_1")
            p2_home = home_scores.get("period_2")
            p2_away = away_scores.get("period_2")

            if p1_home is None or p1_away is None:
                continue

            p1_home = int(p1_home)
            p1_away = int(p1_away)
            p2_home = int(p2_home) if p2_home is not None else 0
            p2_away = int(p2_away) if p2_away is not None else 0

            valid_p1 = (p1_home, p1_away) in [(0, 0), (1, 0), (0, 1)]
            valid_p2 = (p2_home == 0 and p2_away == 0)

            if not (valid_p1 and valid_p2):
                continue

            teams = game.get("teams", {}) or {}
            home_team = (teams.get("home") or {}).get("name", "Home")
            away_team = (teams.get("away") or {}).get("name", "Away")

            msg = (
                f"🏒 <b>ХОККЕЙ • СИГНАЛ</b>\n\n"
                f"🏆 <b>{league_name}</b>\n"
                f"⚔️ <b>{home_team}</b> vs <b>{away_team}</b>\n\n"
                f"📊 1-й период: <b>{p1_home}:{p1_away}</b>\n"
                f"📊 2-й период: <b>0:0</b>\n\n"
                f"⏱ Сейчас идёт <b>2-й период</b>\n\n"
                f"💡 Рекомендация:\n"
                f"Тотал больше 0.5 во 2-м периоде"
            )

            send_telegram(HOCKEY_BOT_TOKEN, msg)
            sent_hockey_matches.add(game_id)
            logger.info(f"[HOCKEY SIGNAL] {home_team} vs {away_team} | P1 {p1_home}:{p1_away}")

        except Exception as e:
            logger.exception(e)

# ---------- LOOPS ----------
def football_monitor_loop():
    while True:
        try:
            process_football_commands()
            if football_state.running:
                check_football()
                self_ping()
        except Exception as e:
            logger.exception(e)
        time.sleep(FOOTBALL_CHECK_INTERVAL)

def hockey_monitor_loop():
    while True:
        try:
            process_hockey_commands()
            if hockey_state.running:
                check_hockey()
        except Exception as e:
            logger.exception(e)
        time.sleep(HOCKEY_CHECK_INTERVAL)

# ---------- MAIN ----------
def main():
    logger.info("Starting Universal Sports Monitor Final Tokens (Football + Hockey)...")
    keep_alive()
    time.sleep(2)

    Thread(target=football_commands_loop, daemon=True).start()
    Thread(target=hockey_commands_loop, daemon=True).start()
    Thread(target=hockey_monitor_loop, daemon=True).start()

    send_telegram(
        FOOTBALL_BOT_TOKEN,
        "🟢 <b>Объединенный бот запущен (Футбол + Хоккей)</b>\n\n"
        "Футбольный мониторинг активен."
    )
    send_telegram(
        HOCKEY_BOT_TOKEN,
        "🟢 <b>Хоккейный модуль активирован в общем боте</b>\n\n"
        "Оба потока работают параллельно."
    )

    football_monitor_loop()

if __name__ == "__main__":
    main()
