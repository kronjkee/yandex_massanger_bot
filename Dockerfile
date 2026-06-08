# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем корневые сертификаты
RUN apt-get update && apt-get install -y ca-certificates && update-ca-certificates

WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY src/ ./src/

EXPOSE 5000

# Запуск через gunicorn для продакшена
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "2", "--timeout", "30", "src.bot:app"]