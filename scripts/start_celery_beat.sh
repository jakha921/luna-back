#!/bin/bash

# Скрипт для запуска Celery Beat

echo "Starting Celery Beat..."

# Проверяем наличие переменных окружения
if [ -z "$REDIS_HOST" ] || [ -z "$REDIS_PORT" ] || [ -z "$REDIS_PASSWORD" ]; then
    echo "Error: Redis environment variables not set"
    exit 1
fi

# Запускаем Celery Beat
celery -A src.tasks.celery_app beat \
    --loglevel=info \
    --scheduler=celery.beat.PersistentScheduler 