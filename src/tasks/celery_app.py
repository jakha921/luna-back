"""
Celery application configuration for background tasks.
"""

import os
from celery import Celery
from celery.schedules import crontab

from src.core.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Создаем экземпляр Celery
celery_app = Celery(
    "luna_terra_backend",
    broker=f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    backend=f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/1",
    include=["src.tasks.balance_sync"]
)

# Конфигурация Celery
celery_app.conf.update(
    # Настройки задач
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Настройки воркера
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    # Настройки планировщика (Beat)
    beat_schedule={
        "sync-balances-hourly": {
            "task": "src.tasks.balance_sync.sync_balances_task",
            "schedule": crontab(minute=0, hour="*"),  # Каждый час
            "options": {"queue": "balance_sync"}
        },
        "sync-balances-daily": {
            "task": "src.tasks.balance_sync.sync_balances_task",
            "schedule": crontab(minute=0, hour=2),  # В 2:00 каждый день
            "options": {"queue": "balance_sync"}
        }
    },
    
    # Настройки очередей
    task_routes={
        "src.tasks.balance_sync.sync_balances_task": {"queue": "balance_sync"},
    },
    
    # Настройки retry
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Настройки логирования
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",
)

# Настройки для разработки
if settings.DEBUG:
    celery_app.conf.update(
        task_always_eager=False,  # Задачи выполняются асинхронно
        task_eager_propagates=True,
    )

logger.info("Celery application configured successfully")


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Настройка периодических задач при запуске Celery."""
    logger.info("Setting up periodic tasks...")
    
    # Добавляем задачу синхронизации балансов каждый час
    sender.add_periodic_task(
        crontab(minute=0, hour="*"),
        sync_balances_task.s(),
        name="sync-balances-hourly"
    )
    
    logger.info("Periodic tasks configured successfully")


@celery_app.task(bind=True)
def debug_task(self):
    """Тестовая задача для проверки работы Celery."""
    logger.info(f"Request: {self.request!r}")
    return "Debug task completed successfully" 