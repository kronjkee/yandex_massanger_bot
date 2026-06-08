import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Токены
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    TRACKER_TOKEN = os.getenv('TRACKER_TOKEN')
    ORG_ID = os.getenv('ORG_ID')

    # Настройки
    WEBHOOK_URL = os.getenv('WEBHOOK_URL')
    PORT = int(os.getenv('PORT', 5000))
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

    # Очереди для поиска
    TASK_QUEUES = os.getenv('TASK_QUEUES', 'SYS,VD,TEST').split(',')

    # API URL
    YANDEX_BOT_API = "https://botapi.messenger.yandex.net/bot/v1/"
    YANDEX_TRACKER_API = "https://api.tracker.yandex.net/v3/"

    @classmethod
    def validate(cls):
        required_vars = ['BOT_TOKEN', 'TRACKER_TOKEN', 'ORG_ID']
        missing = [var for var in required_vars if not getattr(cls, var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")