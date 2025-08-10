#!/bin/bash

# Скрипт для запуска Celery Worker

echo "Starting Celery Worker..."

# Проверяем наличие переменных окружения
if [ -z "$REDIS_HOST" ] || [ -z "$REDIS_PORT" ] || [ -z "$REDIS_PASSWORD" ]; then
    echo "Error: Redis environment variables not set"
    exit 1
fi

# Запускаем Celery Worker
celery -A src.tasks.celery_app worker \
    --loglevel=info \
    --queues=balance_sync,default \
    --concurrency=2 \
    --max-tasks-per-child=1000 \
    --prefetch-multiplier=1 