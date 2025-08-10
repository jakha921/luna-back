# Система синхронизации балансов

## Обзор

Система автоматической синхронизации балансов пользователей из Redis в базу данных PostgreSQL. Обеспечивает надежное сохранение данных даже при недоступности кэша.

## Архитектура

### Компоненты

1. **Celery Worker** - выполняет задачи синхронизации
2. **Celery Beat** - планировщик периодических задач
3. **Redis** - брокер сообщений и кэш данных
4. **PostgreSQL** - основное хранилище данных
5. **API Endpoints** - управление синхронизацией через REST API

### Расписание синхронизации

- **Каждый час** (в 00 минут) - основная синхронизация
- **Каждый день в 2:00** - дополнительная синхронизация
- **Принудительная** - по запросу через API

## Установка и настройка

### 1. Зависимости

```bash
poetry add celery redis
```

### 2. Переменные окружения

```env
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_password

# Celery
CELERY_BROKER_URL=redis://:password@localhost:6379/0
CELERY_RESULT_BACKEND=redis://:password@localhost:6379/1
```

### 3. Запуск сервисов

```bash
# Запуск всех сервисов
docker-compose up -d

# Или отдельно
docker-compose up celery-worker
docker-compose up celery-beat
```

## Использование

### API Endpoints

#### Получение статуса синхронизации
```bash
GET /sync-management/status
```

#### Принудительная синхронизация
```bash
POST /sync-management/force-sync
```

#### Информация о расписании
```bash
GET /sync-management/schedule
```

#### Проверка здоровья системы
```bash
GET /sync-management/health
```

#### Детальная статистика
```bash
GET /sync-management/stats
```

#### Очистка кэша
```bash
DELETE /sync-management/clear-cache
```

### Management команды

#### Синхронизация балансов
```bash
# Обычная синхронизация
python -m src.management.commands.sync_balances

# Принудительная синхронизация
python -m src.management.commands.sync_balances --force

# Тестовый запуск (без изменений)
python -m src.management.commands.sync_balances --dry-run

# Подробный вывод
python -m src.management.commands.sync_balances --verbose
```

#### Проверка здоровья
```bash
python -m src.management.commands.sync_balances health_check
```

### Celery команды

#### Запуск Worker
```bash
celery -A src.tasks.celery_app worker --loglevel=info --queues=balance_sync,default
```

#### Запуск Beat (планировщик)
```bash
celery -A src.tasks.celery_app beat --loglevel=info
```

#### Мониторинг
```bash
# Статус воркеров
celery -A src.tasks.celery_app inspect active

# Статус задач
celery -A src.tasks.celery_app inspect stats

# Очистка результатов
celery -A src.tasks.celery_app purge
```

## Мониторинг и логирование

### Логи

Логи Celery сохраняются в:
- `logs/celery-worker.log`
- `logs/celery-beat.log`

### Метрики

Система предоставляет следующие метрики:

- Количество обработанных записей
- Количество обновленных балансов
- Количество ошибок
- Время выполнения синхронизации
- Статус подключений к Redis и БД

### Алерты

Настройте алерты для:
- Ошибок синхронизации
- Долгого времени выполнения
- Недоступности Redis или БД

## Отказоустойчивость

### Стратегии восстановления

1. **Retry механизм** - автоматические повторные попытки при ошибках
2. **Fallback на БД** - при недоступности Redis данные берутся из БД
3. **Резервное копирование** - регулярное сохранение в БД
4. **Мониторинг здоровья** - постоянная проверка состояния системы

### Обработка ошибок

- **Redis недоступен** - синхронизация откладывается, данные берутся из БД
- **БД недоступна** - ошибка логируется, задача повторяется
- **Некорректные данные** - запись пропускается, ошибка логируется

## Производительность

### Оптимизации

- **Batch обновления** - массовые обновления в БД
- **Connection pooling** - переиспользование соединений
- **Async операции** - асинхронная обработка
- **Кэширование** - кэш часто используемых данных

### Рекомендации

- Мониторьте использование памяти Redis
- Настройте TTL для ключей кэша
- Регулярно очищайте старые данные
- Используйте отдельные очереди для разных типов задач

## Безопасность

### Аутентификация

- Redis защищен паролем
- API endpoints требуют аутентификации (если настроена)

### Валидация данных

- Проверка корректности балансов
- Валидация telegram_id
- Защита от SQL injection

## Разработка

### Добавление новых задач

1. Создайте функцию в `src/tasks/`
2. Добавьте декоратор `@celery_app.task`
3. Настройте расписание в `celery_app.py`
4. Добавьте тесты

### Тестирование

```bash
# Запуск тестов
pytest tests/test_balance_sync.py -v

# Тестирование с реальными данными
python -m src.management.commands.sync_balances --dry-run
```

### Отладка

```bash
# Подробные логи
celery -A src.tasks.celery_app worker --loglevel=debug

# Инспекция задач
celery -A src.tasks.celery_app inspect active

# Мониторинг в реальном времени
celery -A src.tasks.celery_app events
```

## Troubleshooting

### Частые проблемы

1. **Redis connection refused**
   - Проверьте настройки Redis
   - Убедитесь что Redis запущен

2. **Database connection error**
   - Проверьте настройки БД
   - Убедитесь что БД доступна

3. **Tasks not executing**
   - Проверьте статус воркеров
   - Убедитесь что Beat запущен

4. **High memory usage**
   - Настройте TTL для ключей
   - Очистите старые данные

### Полезные команды

```bash
# Проверка статуса всех сервисов
docker-compose ps

# Просмотр логов
docker-compose logs celery-worker
docker-compose logs celery-beat

# Перезапуск сервисов
docker-compose restart celery-worker celery-beat

# Проверка здоровья
curl http://localhost:8000/sync-management/health
```

## Конфигурация

### Настройки Celery

```python
# src/tasks/celery_app.py
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)
```

### Настройки расписания

```python
beat_schedule={
    "sync-balances-hourly": {
        "task": "src.tasks.balance_sync.sync_balances_task",
        "schedule": crontab(minute=0, hour="*"),
        "options": {"queue": "balance_sync"}
    },
    "sync-balances-daily": {
        "task": "src.tasks.balance_sync.sync_balances_task",
        "schedule": crontab(minute=0, hour=2),
        "options": {"queue": "balance_sync"}
    }
}
```

## Заключение

Система синхронизации балансов обеспечивает надежное сохранение данных пользователей с автоматическим резервным копированием и мониторингом. Используйте API endpoints и management команды для управления системой. 