import requests
from typing import Optional, Dict, Any, List  # <-- Добавили List

from src.config import Config
from src.utils import logger, TaskCache

class TrackerClient:
    """Клиент для API Яндекс Трекера"""

    def __init__(self):
        self.token = Config.TRACKER_TOKEN
        self.org_id = Config.ORG_ID
        self.base_url = "https://api.tracker.yandex.net/v3/"
        self.cache = TaskCache()

        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'OAuth {self.token}',
            'X-Org-ID': self.org_id,
            'Content-Type': 'application/json'
        })

    def get_task(self, task_key: str) -> Optional[Dict[str, Any]]:
        """Получает информацию о задаче"""
        # Проверка кэша
        cached = self.cache.get(task_key)
        if cached:
            return cached

        url = f"{self.base_url}issues/{task_key}"

        try:
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()

                task_info = {
                    'key': task_key,
                    'summary': data.get('summary', 'Без названия'),
                    'status': data.get('status', {}).get('display', 'Неизвестно'),
                    'assignee': data.get('assignee', {}).get('display', 'Не назначен'),
                    'priority': data.get('priority', {}).get('display', 'Не указан'),
                    'created_by': data.get('createdBy', {}).get('display', ''),
                    'queue': data.get('queue', {}).get('display', ''),
                    'url': f"https://tracker.yandex.ru/{task_key}"
                }

                self.cache.set(task_key, task_info)
                return task_info

            elif response.status_code == 404:
                return {'error': 'not_found', 'key': task_key}
            else:
                logger.error(f"Tracker error: {response.status_code}")
                return {'error': 'api_error', 'key': task_key}

        except Exception as e:
            logger.error(f"Error fetching {task_key}: {e}")
            return {'error': 'connection_error', 'key': task_key}

    def format_task_message(self, task_info: Dict[str, Any]) -> str:
        """Форматирует информацию о задаче с ссылкой в заголовке"""
        if 'error' in task_info:
            return f"❌ Задача {task_info['key']} не найдена"

        # Заголовок задачи теперь кликабельный
        lines = [
            f"📌 **[#{task_info['key']} {task_info['summary']}]({task_info['url']})**",
            f"📊 Статус: **{task_info['status']}**",
            f"👤 Исполнитель: {task_info['assignee']}",
            f"⚡ Приоритет: {task_info['priority']}"
        ]

        if task_info.get('created_by'):
            lines.append(f"👤 Создатель: {task_info['created_by']}")
        if task_info.get('queue'):
            lines.append(f"🗂️ Очередь: {task_info['queue']}")

        return "\n".join(lines)

    def format_multiple_tasks(self, tasks_info: List[Dict[str, Any]]) -> str:
        """Форматирует список задач с ссылками"""
        lines = ["🔍 **Найденные задачи:**"]

        for info in tasks_info:
            if 'error' not in info:
                # Каждая задача со ссылкой в заголовке
                lines.append(
                    f"• **[#{info['key']} {info['summary']}]({info['url']})**\n"
                    f"  Статус: {info['status']}, Исполнитель: {info['assignee']}"
                )
            else:
                lines.append(f"• ❌ {info['key']}: не найдена")

        return "\n\n".join(lines)

    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()