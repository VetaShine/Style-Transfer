import logging
from logging.handlers import TimedRotatingFileHandler
import os
from datetime import datetime

# Путь к директории логов
LOG_DIR = "/app/logs_bot"
LOG_FILENAME = "bot.log"

# Убедимся, что директория существует
os.makedirs(LOG_DIR, exist_ok=True)

# Путь к файлу лога
log_file_path = os.path.join(LOG_DIR, LOG_FILENAME)

# Настройка логирования
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Формат логов
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

class CustomTimedRotatingFileHandler(TimedRotatingFileHandler):
    """
    Кастомный обработчик логов, который изменяет имя файла лога в зависимости от даты.
    """
    def __init__(self, filename, when='midnight', interval=1, backupCount=7, encoding=None, delay=False, utc=False, atTime=None):
        super().__init__(filename, when, interval, backupCount, encoding, delay, utc, atTime)
        self.suffix = "%Y-%m-%d"  # Формат суффикса даты

    def rotation_filename(self, default_name):
        """
        Переопределение имени ротационного файла.
        """
        return default_name

# Настройка TimedRotatingFileHandler
file_handler = CustomTimedRotatingFileHandler(
    filename=log_file_path,
    when="midnight",      # Ротация каждый день в полночь
    interval=1,           # Интервал в 1 день
    backupCount=7,        # Хранить логи за последние 7 дней
    encoding='utf-8',
    utc=True              # Использовать UTC время. Уберите или измените на False для локального времени
)

file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Логирование ошибок на консоль
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

logger.info("Система логирования инициализирована.")
logger.info("Приложение запущено.")

# Функция для получения логера
def get_logger():
    return logger
