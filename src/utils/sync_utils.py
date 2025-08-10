"""
Утилиты для синхронизации балансов между Redis и базой данных.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from src.core.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BalanceSyncManager:
    """Менеджер для управления синхронизацией балансов."""
    
    def __init__(self):
        self.redis_client: Optional[Redis] = None
        self.last_sync_time: Optional[datetime] = None
        self.sync_stats: Dict = {}
    
    async def __aenter__(self):
        """Асинхронный контекстный менеджер."""
        await self._connect_redis()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие соединений."""
        await self._disconnect_redis()
    
    async def _connect_redis(self):
        """Подключение к Redis."""
        try:
            self.redis_client = Redis(
                host=settings.REDIS_HOST,
                port=int(settings.REDIS_PORT),
                password=settings.REDIS_PASSWORD,
                decode_responses=True
            )
            # Проверяем подключение
            await self.redis_client.ping()
            logger.info("Successfully connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def _disconnect_redis(self):
        """Отключение от Redis."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")
    
    async def get_sync_status(self) -> Dict:
        """
        Получает статус последней синхронизации.
        
        Returns:
            Dict: Статус синхронизации
        """
        if not self.redis_client:
            await self._connect_redis()
        
        try:
            # Получаем время последней синхронизации
            last_sync_key = "balance_sync:last_sync"
            last_sync_str = await self.redis_client.get(last_sync_key)
            
            if last_sync_str:
                self.last_sync_time = datetime.fromisoformat(last_sync_str)
            
            # Получаем статистику
            stats_key = "balance_sync:last_stats"
            stats_str = await self.redis_client.get(stats_key)
            
            if stats_str:
                import json
                self.sync_stats = json.loads(stats_str)
            
            return {
                "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
                "last_sync_stats": self.sync_stats,
                "redis_connected": True
            }
            
        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            return {
                "last_sync_time": None,
                "last_sync_stats": {},
                "redis_connected": False,
                "error": str(e)
            }
    
    async def update_sync_status(self, sync_stats: Dict):
        """
        Обновляет статус синхронизации в Redis.
        
        Args:
            sync_stats: Статистика синхронизации
        """
        if not self.redis_client:
            await self._connect_redis()
        
        try:
            # Сохраняем время последней синхронизации
            last_sync_key = "balance_sync:last_sync"
            await self.redis_client.set(
                last_sync_key,
                datetime.utcnow().isoformat(),
                ex=86400  # 24 часа
            )
            
            # Сохраняем статистику
            stats_key = "balance_sync:last_stats"
            import json
            await self.redis_client.set(
                stats_key,
                json.dumps(sync_stats),
                ex=86400  # 24 часа
            )
            
            self.last_sync_time = datetime.utcnow()
            self.sync_stats = sync_stats
            
            logger.info("Sync status updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating sync status: {e}")
            raise
    
    async def should_sync(self, force: bool = False, min_interval_hours: int = 1) -> bool:
        """
        Проверяет, нужно ли выполнить синхронизацию.
        
        Args:
            force: Принудительная синхронизация
            min_interval_hours: Минимальный интервал между синхронизациями (часы)
            
        Returns:
            bool: True если нужно синхронизировать
        """
        if force:
            return True
        
        if not self.last_sync_time:
            return True
        
        time_since_last_sync = datetime.utcnow() - self.last_sync_time
        min_interval = timedelta(hours=min_interval_hours)
        
        return time_since_last_sync >= min_interval
    
    async def get_redis_info(self) -> Dict:
        """
        Получает информацию о Redis.
        
        Returns:
            Dict: Информация о Redis
        """
        if not self.redis_client:
            await self._connect_redis()
        
        try:
            info = await self.redis_client.info()
            keys_count = len(await self.redis_client.keys("*"))
            
            return {
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "total_keys": keys_count,
                "uptime_in_seconds": info.get("uptime_in_seconds")
            }
            
        except Exception as e:
            logger.error(f"Error getting Redis info: {e}")
            return {
                "error": str(e)
            }


async def get_balance_sync_summary() -> Dict:
    """
    Получает сводку по синхронизации балансов.
    
    Returns:
        Dict: Сводка синхронизации
    """
    async with BalanceSyncManager() as manager:
        sync_status = await manager.get_sync_status()
        redis_info = await manager.get_redis_info()
        
        return {
            "sync_status": sync_status,
            "redis_info": redis_info,
            "timestamp": datetime.utcnow().isoformat()
        }


async def force_balance_sync() -> Dict:
    """
    Принудительная синхронизация балансов.
    
    Returns:
        Dict: Результат синхронизации
    """
    from src.tasks.balance_sync import sync_balances_task
    
    try:
        # Запускаем задачу синхронизации
        result = sync_balances_task.delay(force_sync=True)
        
        return {
            "task_id": result.id,
            "status": "started",
            "message": "Balance sync task started",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error starting balance sync task: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


def get_sync_schedule_info() -> Dict:
    """
    Получает информацию о расписании синхронизации.
    
    Returns:
        Dict: Информация о расписании
    """
    return {
        "hourly_sync": {
            "schedule": "Every hour at minute 0",
            "task": "src.tasks.balance_sync.sync_balances_task",
            "enabled": True
        },
        "daily_sync": {
            "schedule": "Every day at 2:00 AM",
            "task": "src.tasks.balance_sync.sync_balances_task",
            "enabled": True
        },
        "cleanup_task": {
            "schedule": "Manual",
            "task": "src.tasks.balance_sync.cleanup_old_balances_task",
            "enabled": False
        },
        "health_check": {
            "schedule": "Manual",
            "task": "src.tasks.balance_sync.health_check_task",
            "enabled": True
        }
    } 