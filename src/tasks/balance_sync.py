"""
Celery tasks for balance synchronization from Redis to database.
"""

import asyncio
from datetime import datetime
from typing import Dict, Optional
from celery import current_task
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from src.core.config import settings
from src.db.session import get_session
from src.repositories.user import UserRepository
from src.utils.redis_sync import get_all_telegram_balances
from src.utils.logger import get_logger
from .celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    bind=True,
    name="src.tasks.balance_sync.sync_balances_task",
    max_retries=3,
    default_retry_delay=300,  # 5 минут
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True
)
def sync_balances_task(self, force_sync: bool = False) -> Dict:
    """
    Задача синхронизации балансов пользователей из Redis в базу данных.
    
    Args:
        force_sync: Принудительная синхронизация (игнорирует время последней синхронизации)
        
    Returns:
        Dict: Статистика синхронизации
    """
    task_id = self.request.id
    logger.info(f"Starting balance sync task {task_id} (force_sync={force_sync})")
    
    try:
        # Запускаем асинхронную функцию в синхронном контексте
        result = asyncio.run(_sync_balances_async(force_sync))
        
        logger.info(f"Balance sync task {task_id} completed successfully: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Balance sync task {task_id} failed: {exc}")
        
        # Retry логика
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying balance sync task {task_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc)
        else:
            logger.error(f"Balance sync task {task_id} failed after {self.max_retries} retries")
            raise


async def _sync_balances_async(force_sync: bool = False) -> Dict:
    """
    Асинхронная функция синхронизации балансов.
    
    Args:
        force_sync: Принудительная синхронизация
        
    Returns:
        Dict: Статистика синхронизации
    """
    start_time = datetime.utcnow()
    sync_stats = {
        "start_time": start_time.isoformat(),
        "end_time": None,
        "total_processed": 0,
        "updated_count": 0,
        "not_found_count": 0,
        "error_count": 0,
        "redis_keys_found": 0,
        "sync_duration_seconds": 0,
        "status": "failed"
    }
    
    try:
        # Получаем сессию базы данных
        async with get_session() as session:
            user_repo = UserRepository(db=session)
            
            # Получаем данные из Redis
            redis_data = await _get_redis_balances()
            sync_stats["redis_keys_found"] = len(redis_data)
            
            if not redis_data:
                logger.info("No balance data found in Redis")
                sync_stats.update({
                    "status": "completed",
                    "end_time": datetime.utcnow().isoformat(),
                    "sync_duration_seconds": (datetime.utcnow() - start_time).total_seconds()
                })
                return sync_stats
            
            # Синхронизируем данные
            sync_result = await user_repo.sync_balances_from_redis(redis_data)
            
            # Обновляем статистику
            sync_stats.update(sync_result)
            sync_stats["total_processed"] = len(redis_data)
            
            # Проверяем успешность синхронизации
            if sync_stats["error_count"] == 0:
                sync_stats["status"] = "completed"
                logger.info(f"Balance sync completed successfully: {sync_stats}")
            else:
                sync_stats["status"] = "completed_with_errors"
                logger.warning(f"Balance sync completed with errors: {sync_stats}")
            
            sync_stats.update({
                "end_time": datetime.utcnow().isoformat(),
                "sync_duration_seconds": (datetime.utcnow() - start_time).total_seconds()
            })
            
            return sync_stats
            
    except RedisConnectionError as e:
        logger.error(f"Redis connection error during balance sync: {e}")
        sync_stats.update({
            "status": "redis_error",
            "error_message": str(e),
            "end_time": datetime.utcnow().isoformat(),
            "sync_duration_seconds": (datetime.utcnow() - start_time).total_seconds()
        })
        return sync_stats
        
    except Exception as e:
        logger.error(f"Unexpected error during balance sync: {e}")
        sync_stats.update({
            "status": "error",
            "error_message": str(e),
            "end_time": datetime.utcnow().isoformat(),
            "sync_duration_seconds": (datetime.utcnow() - start_time).total_seconds()
        })
        return sync_stats


async def _get_redis_balances() -> Dict[str, str]:
    """
    Получает балансы пользователей из Redis.
    
    Returns:
        Dict[str, str]: Словарь {telegram_id: balance}
    """
    try:
        # Создаем подключение к Redis
        redis_client = Redis(
            host=settings.REDIS_HOST,
            port=int(settings.REDIS_PORT),
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        
        # Получаем все балансы
        balances = await get_all_telegram_balances(redis_client)
        
        # Закрываем соединение
        await redis_client.close()
        
        return balances
        
    except Exception as e:
        logger.error(f"Error getting Redis balances: {e}")
        raise


@celery_app.task(
    bind=True,
    name="src.tasks.balance_sync.cleanup_old_balances_task",
    max_retries=2,
    default_retry_delay=60
)
def cleanup_old_balances_task(self, days_old: int = 7) -> Dict:
    """
    Задача очистки старых балансов из Redis.
    
    Args:
        days_old: Количество дней, после которых данные считаются старыми
        
    Returns:
        Dict: Статистика очистки
    """
    task_id = self.request.id
    logger.info(f"Starting cleanup task {task_id} for balances older than {days_old} days")
    
    try:
        result = asyncio.run(_cleanup_old_balances_async(days_old))
        logger.info(f"Cleanup task {task_id} completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Cleanup task {task_id} failed: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        else:
            raise


async def _cleanup_old_balances_async(days_old: int) -> Dict:
    """
    Асинхронная функция очистки старых балансов.
    
    Args:
        days_old: Количество дней
        
    Returns:
        Dict: Статистика очистки
    """
    # TODO: Реализовать очистку старых данных
    # Пока возвращаем заглушку
    return {
        "cleaned_keys": 0,
        "days_old": days_old,
        "status": "not_implemented"
    }


@celery_app.task(
    bind=True,
    name="src.tasks.balance_sync.health_check_task"
)
def health_check_task(self) -> Dict:
    """
    Задача проверки здоровья системы синхронизации.
    
    Returns:
        Dict: Статус здоровья
    """
    task_id = self.request.id
    logger.info(f"Starting health check task {task_id}")
    
    try:
        result = asyncio.run(_health_check_async())
        logger.info(f"Health check task {task_id} completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Health check task {task_id} failed: {exc}")
        return {
            "status": "unhealthy",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }


async def _health_check_async() -> Dict:
    """
    Асинхронная функция проверки здоровья.
    
    Returns:
        Dict: Статус здоровья
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    try:
        # Проверяем подключение к Redis
        redis_client = Redis(
            host=settings.REDIS_HOST,
            port=int(settings.REDIS_PORT),
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        
        # Проверяем ping
        ping_result = await redis_client.ping()
        health_status["checks"]["redis"] = "ok" if ping_result else "failed"
        
        # Получаем количество ключей
        keys_count = len(await redis_client.keys("*"))
        health_status["checks"]["redis_keys_count"] = keys_count
        
        await redis_client.close()
        
        # Проверяем подключение к базе данных
        async with get_session() as session:
            # Простой запрос для проверки подключения
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            health_status["checks"]["database"] = "ok" if result else "failed"
        
        # Если все проверки прошли успешно
        if all(check == "ok" for check in health_status["checks"].values() if isinstance(check, str)):
            health_status["status"] = "healthy"
        else:
            health_status["status"] = "unhealthy"
            
        return health_status
        
    except Exception as e:
        health_status.update({
            "status": "unhealthy",
            "error": str(e)
        })
        return health_status 