from flask import Flask, request, jsonify
import requests
import threading
import json
import traceback
import time
from collections import defaultdict

from src.config import Config
from src.tracker_client import TrackerClient
from src.utils import logger, find_task_keys

# Инициализация
app = Flask(__name__)
Config.validate()

tracker = TrackerClient()

BOT_API = Config.YANDEX_BOT_API

# Кэш обработанных сообщений (чтобы не отвечать дважды)
processed_messages = defaultdict(float)
PROCESSED_EXPIRY = 60

def is_message_processed(message_id: int) -> bool:
    """Проверяет, обрабатывали ли мы это сообщение"""
    now = time.time()
    # Очищаем старые записи
    expired = [mid for mid, ts in processed_messages.items() if now - ts > PROCESSED_EXPIRY]
    for mid in expired:
        del processed_messages[mid]

    return message_id in processed_messages

def mark_message_processed(message_id: int):
    """Отмечает сообщение как обработанное"""
    processed_messages[message_id] = time.time()

def send_message(chat_id: str, text: str, thread_target: int = None):
    """Отправляет текстовое сообщение в чат"""
    url = BOT_API + "messages/sendText/"

    payload = {
        "chat_id": str(chat_id),
        "text": text
    }

    if thread_target is not None:
        payload["thread_id"] = thread_target

    headers = {
        'Authorization': f'OAuth {Config.BOT_TOKEN}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)

        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                logger.debug(f"✅ Message sent")
                return result
            else:
                logger.error(f"❌ API error: {result.get('description')}")
                return None
        else:
            logger.error(f"❌ HTTP error: {response.status_code}")
            return None

    except Exception as e:
        logger.error(f"❌ Error sending message: {e}")
        return None

def _handle_update(data):
    """Обработка входящего обновления"""
    try:
        if 'updates' not in data:
            return

        for update in data['updates']:
            if 'message_id' not in update:
                continue

            message_id = update.get('message_id')

            # Защита от повторной обработки
            if is_message_processed(message_id):
                logger.debug(f"Message {message_id} already processed, skipping")
                continue

            mark_message_processed(message_id)

            # Извлекаем данные
            chat_id = None
            existing_thread_id = None

            if 'chat' in update:
                chat_field = update['chat']
                if isinstance(chat_field, dict):
                    chat_id = chat_field.get('id')
                    existing_thread_id = chat_field.get('thread_id')

            if not chat_id:
                logger.warning("No chat_id in update")
                continue

            text = update.get('text', '')

            # Определяем цель для ответа
            if existing_thread_id:
                thread_target = existing_thread_id
                logger.debug(f"Message in thread {existing_thread_id}")
            else:
                thread_target = message_id
                logger.debug(f"New message, will create thread")

            # Ищем уникальные ключи
            keys = find_task_keys(text)
            if keys:
                logger.info(f"🔍 Processing {len(keys)} unique keys: {keys}")

                # Получаем информацию по каждой уникальной задаче
                tasks_info = []
                for key in keys:
                    info = tracker.get_task(key)
                    if info and 'error' not in info:
                        tasks_info.append(info)
                    else:
                        tasks_info.append({'key': key, 'error': 'not_found'})

                # Отправляем ответ
                if len(tasks_info) > 1:
                    response_text = tracker.format_multiple_tasks(tasks_info)
                    logger.info(f"📤 Sending multi-task response with {len(tasks_info)} tasks")
                else:
                    response_text = tracker.format_task_message(tasks_info[0])
                    logger.info(f"📤 Sending single task response")

                send_message(chat_id, response_text, thread_target)

    except Exception as e:
        logger.error(f"Error in handler: {e}")
        logger.error(traceback.format_exc())

@app.route('/webhook', methods=['POST'])
def webhook():
    """Вебхук для приема обновлений"""
    data = request.json
    thread = threading.Thread(target=_handle_update, args=(data,))
    thread.daemon = True
    thread.start()
    return jsonify({'ok': True})

@app.route('/health', methods=['GET'])
def health():
    """Проверка здоровья"""
    return jsonify({
        'status': 'healthy',
        'version': '2.1'
    })

def setup_webhook():
    """Установка вебхука"""
    url = "https://botapi.messenger.yandex.net/bot/v1/self/update/"
    headers = {
        'Authorization': f'OAuth {Config.BOT_TOKEN}',
        'Content-Type': 'application/json'
    }

    payload = {"webhook_url": Config.WEBHOOK_URL}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            logger.info(f"✅ Webhook set to {Config.WEBHOOK_URL}")
        else:
            logger.error(f"❌ Webhook error: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Webhook setup error: {e}")

if __name__ == '__main__':
    logger.info("🚀 Starting Yandex Tracker Bot v2.1")
    logger.info(f"📋 Watching queues: {Config.TASK_QUEUES}")
    setup_webhook()
    app.run(host='0.0.0.0', port=Config.PORT, debug=Config.DEBUG)