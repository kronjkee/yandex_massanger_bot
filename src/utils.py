import re
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Set

from src.config import Config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def find_task_keys(text: str) -> List[str]:
    """
    Ищет уникальные ключи задач из разрешенных очередей
    Формат: QUEUE-123 (например, SYS-751, VD-2470)
    """
    # Создаем множество разрешенных очередей
    allowed_queues = set(Config.TASK_QUEUES)

    # Паттерн для поиска ключей: буквы-цифры
    pattern = r'\b([A-Za-z]+)-([0-9]+)\b'

    found_keys = set()  # используем set для уникальности

    for match in re.finditer(pattern, text, re.IGNORECASE):
        queue = match.group(1).upper()
        number = match.group(2)

        # Проверяем, разрешена ли очередь
        if queue in allowed_queues:
            full_key = f"{queue}-{number}"
            found_keys.add(full_key)

    # Преобразуем в список для сохранения порядка (но порядок не гарантирован)
    result = list(found_keys)

    if result:
        logger.info(f"🔍 Found unique keys: {result}")
    else:
        logger.debug("No keys found")

    return result

class TaskCache:
    """Кэш для задач Трекера"""
    def __init__(self, ttl_minutes: int = 5):
        self.cache = {}
        self.ttl = timedelta(minutes=ttl_minutes)

    def get(self, key: str) -> Optional[dict]:
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                logger.debug(f"Cache hit for {key}")
                return data
            else:
                del self.cache[key]
        return None

    def set(self, key: str, data: dict):
        self.cache[key] = (data, datetime.now())
        logger.debug(f"Cached {key}")