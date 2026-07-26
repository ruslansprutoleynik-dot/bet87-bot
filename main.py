
import os
import time
import logging
import requests
from telegram import Bot

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем переменные окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Инициализация Telegram бота
bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None


def send_telegram_message(text):
  if not bot or not TELEGRAM_CHAT_ID:
    logger.error("Telegram токен или Chat ID не заданы!")
    return
  try:
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)
  except Exception as e:
    logger.error(f"Ошибка отправки сообщения в Telegram: {e}")


def fetch_matches():
  """Функция получения матчей (заглушка или ваш реальный API-запрос)"""
  try:
    # Пример структуры, которая может возвращаться.
    # Если здесь прилетит некорректный элемент (например, чистая строка), защита ниже не даст боту упасть.
    response = requests.get(
        "https://api.example.com/matches", timeout=10
    )  # Замените на ваш реальный URL
    if response.status_code == 200:
      return response.json()
  except Exception as e:
    logger.error(f"Ошибка запроса данных: {e}")
  return []


def analyze_matches():
  logger.info("Начало цикла проверки матчей...")

  # Получаем данные
  data = fetch_matches()

  # Защита: если данные пришли не в виде списка, приводим к пустому списку
  if not isinstance(data, list):
    data = []

  logger.info(f"Получено матчей для анализа: {len(data)}")

  for match in data:
    # ГЛАВНАЯ ЗАЩИТА: проверяем, что элемент является словарем, а не строкой
    if not isinstance(match, dict):
      logger.warning(
          f"Пропущен некорректный элемент данных (ожидался словарь, получено"
          f" {type(match)}): {match}"
      )
      continue

    # Безопасное извлечение данных через .get()
    match_id = match.get("id", "Неизвестно")
    home_team = match.get("home_team", "Хозяева")
    away_team = match.get("away_team", "Гости")

    # Логика анализа матча...
    logger.info(f"Анализируем матч: {home_team} vs {away_team} (ID: {match_id})")


def main():
  logger.info("Бот успешно запущен на Render и готов к работе!")
  send_telegram_message("🤖 Бот успешно запущен и начал мониторинг!")

  while True:
    try:
      analyze_matches()
    except Exception as e:
      logger.error(f"Ошибка во время выполнения цикла: {e}")

    logger.info("Пауза цикла 60 секунд...")
    time.sleep(60)


if __name__ == "__main__":
  main()
 ⁠# update
