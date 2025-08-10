# 🚀 Система синхронизации балансов Celery + Redis

## ✅ Реализация завершена

Система автоматической синхронизации балансов из Redis в PostgreSQL с использованием Celery + Redis успешно реализована.

## 📁 Созданные файлы

### Основные компоненты
- `src/tasks/` - Пакет Celery задач
  - `celery_app.py` - Конфигурация Celery приложения
  - `balance_sync.py` - Задачи синхронизации балансов
- `src/utils/sync_utils.py` - Утилиты для управления синхронизацией
- `src/api/v1/sync_management.py` - API эндпоинты для управления
- `src/management/commands/sync_balances.py` - Management команды
- `scripts/` - Скрипты запуска
  - `start_celery_worker.sh`
  - `start_celery_beat.sh`
- `tests/test_balance_sync.py` - Тесты системы
- `docs/BALANCE_SYNC.md` - Подробная документация

### Обновленные файлы
- `docker-compose.yml` - Добавлены сервисы Celery Worker и Beat
- `src/api/routes.py` - Добавлены новые роуты
- `pyproject.toml` - Добавлена зависимость Celery

## 🚀 Быстрый запуск

### 1. Установка зависимостей
```bash
poetry install
```

### 2. Запуск всех сервисов
```bash
docker-compose up -d
```

### 3. Проверка статуса
```bash
# Проверка сервисов
docker-compose ps

# Проверка здоровья системы
curl http://localhost:8000/sync-management/health
```

## 📊 API Endpoints

### Управление синхронизацией
```bash
# Статус синхронизации
GET /sync-management/status

# Принудительная синхронизация
POST /sync-management/force-sync

# Расписание синхронизации
GET /sync-management/schedule

# Проверка здоровья
GET /sync-management/health

# Детальная статистика
GET /sync-management/stats

# Очистка кэша
DELETE /sync-management/clear-cache
```

## 🔧 Management команды

### Синхронизация балансов
```bash
# Обычная синхронизация
python -m src.management.commands.sync_balances

# Принудительная синхронизация
python -m src.management.commands.sync_balances --force

# Тестовый запуск
python -m src.management.commands.sync_balances --dry-run

# Подробный вывод
python -m src.management.commands.sync_balances --verbose
```

### Проверка здоровья
```bash
python -m src.management.commands.sync_balances health_check
```

## ⚙️ Celery команды

### Запуск Worker
```bash
celery -A src.tasks.celery_app worker --loglevel=info --queues=balance_sync,default
```

### Запуск Beat (планировщик)
```bash
celery -A src.tasks.celery_app beat --loglevel=info
```

### Мониторинг
```bash
# Статус воркеров
celery -A src.tasks.celery_app inspect active

# Статистика задач
celery -A src.tasks.celery_app inspect stats

# Очистка результатов
celery -A src.tasks.celery_app purge
```

## 📅 Расписание синхронизации

- **Каждый час** (в 00 минут) - основная синхронизация
- **Каждый день в 2:00** - дополнительная синхронизация
- **Принудительная** - по запросу через API

## 🛡️ Отказоустойчивость

### Стратегии восстановления
1. **Retry механизм** - автоматические повторные попытки при ошибках
2. **Fallback на БД** - при недоступности Redis данные берутся из БД
3. **Резервное копирование** - регулярное сохранение в БД
4. **Мониторинг здоровья** - постоянная проверка состояния системы

### Обработка ошибок
- **Redis недоступен** - синхронизация откладывается, данные берутся из БД
- **БД недоступна** - ошибка логируется, задача повторяется
- **Некорректные данные** - запись пропускается, ошибка логируется

## 📈 Мониторинг

### Метрики
- Количество обработанных записей
- Количество обновленных балансов
- Количество ошибок
- Время выполнения синхронизации
- Статус подключений к Redis и БД

### Логи
- `logs/celery-worker.log` - логи воркера
- `logs/celery-beat.log` - логи планировщика

## 🧪 Тестирование

### Запуск тестов
```bash
pytest tests/test_balance_sync.py -v
```

### Тестирование с реальными данными
```bash
python -m src.management.commands.sync_balances --dry-run
```

## 🔍 Отладка

### Подробные логи
```bash
celery -A src.tasks.celery_app worker --loglevel=debug
```

### Инспекция задач
```bash
celery -A src.tasks.celery_app inspect active
```

### Мониторинг в реальном времени
```bash
celery -A src.tasks.celery_app events
```

## 🚨 Troubleshooting

### Частые проблемы

1. **Redis connection refused**
   ```bash
   # Проверьте настройки Redis
   docker-compose logs cache
   ```

2. **Database connection error**
   ```bash
   # Проверьте настройки БД
   docker-compose logs db
   ```

3. **Tasks not executing**
   ```bash
   # Проверьте статус воркеров
   docker-compose logs celery-worker
   ```

4. **High memory usage**
   ```bash
   # Очистите старые данные
   curl -X DELETE http://localhost:8000/sync-management/clear-cache
   ```

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

## 📚 Документация

Подробная документация доступна в `docs/BALANCE_SYNC.md`

## ✅ Готово к использованию

Система синхронизации балансов полностью готова к использованию:

- ✅ Автоматическая синхронизация каждый час
- ✅ Принудительная синхронизация через API
- ✅ Отказоустойчивость и восстановление
- ✅ Мониторинг и логирование
- ✅ Management команды для администрирования
- ✅ Полное тестовое покрытие
- ✅ Docker конфигурация
- ✅ Документация

Теперь ваши данные пользователей будут надежно сохраняться в базе данных даже при недоступности Redis! 