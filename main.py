

        except requests.exceptions.Timeout:
            logging.warning("Предупреждение: Сервер статистики не ответил вовремя (таймаут). Идем дальше...")
        except Exception as e:
            logging.error(f"Ошибка в цикле сканирования: {e}")

        # Пауза 60 секунд перед следующей проверкой
        time.sleep(60)

if __name__ == "__main__":
    logging.info("Запуск веб-сервера для удержания бодрствования (KeepAlive)...")
    keep_alive()
    
    # Приветствие отправляется в Telegram ОДИН РАЗ при старте бота
    send_telegram_message("🟢 <b>Бот
