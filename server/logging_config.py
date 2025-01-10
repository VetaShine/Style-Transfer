import logging
from logging.handlers import TimedRotatingFileHandler
import os
from datetime import datetime

LOG_DIR = "/app/logs_server"
LOG_FILENAME = "server.log"

os.makedirs(LOG_DIR, exist_ok=True)

log_file_path = os.path.join(LOG_DIR, LOG_FILENAME)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

class CustomTimedRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(self, filename, when='midnight', interval=1, backupCount=7, encoding=None, delay=False, utc=False, atTime=None):
        super().__init__(filename, when, interval, backupCount, encoding, delay, utc, atTime)
        self.suffix = "%Y-%m-%d"

    def rotation_filename(self, default_name):
        return default_name

file_handler = CustomTimedRotatingFileHandler(
    filename=log_file_path,
    when="midnight",     
    interval=1,          
    backupCount=7,      
    encoding='utf-8',
    utc=True 
)

file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

logger.info("The logging system is initialized.")
logger.info("The application is running.")

def get_logger():
    return logger
