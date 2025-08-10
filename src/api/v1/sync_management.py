"""
API endpoints for balance synchronization management.
"""

from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis

from src.api.deps import get_redis_client
from src.schemas.common import IGetResponseBase
from src.utils.sync_utils import (
    get_balance_sync_summary,
    force_balance_sync,
    get_sync_schedule_info
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/sync-management", tags=["Sync Management"])


@router.get(
    "/status",
    response_description="Get balance sync status and statistics",
    response_model=IGetResponseBase[Dict],
    summary="Get sync status"
)
async def get_sync_status() -> IGetResponseBase[Dict]:
    """
    Получает статус синхронизации балансов и статистику.
    
    Returns:
        IGetResponseBase[Dict]: Статус синхронизации
    """
    try:
        summary = await get_balance_sync_summary()
        return IGetResponseBase(data=summary)
        
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting sync status: {str(e)}"
        )


@router.post(
    "/force-sync",
    response_description="Force balance synchronization",
    response_model=IGetResponseBase[Dict],
    summary="Force sync balances"
)
async def force_sync_balances() -> IGetResponseBase[Dict]:
    """
    Принудительно запускает синхронизацию балансов.
    
    Returns:
        IGetResponseBase[Dict]: Результат запуска синхронизации
    """
    try:
        result = await force_balance_sync()
        return IGetResponseBase(data=result)
        
    except Exception as e:
        logger.error(f"Error forcing sync: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error forcing sync: {str(e)}"
        )


@router.get(
    "/schedule",
    response_description="Get sync schedule information",
    response_model=IGetResponseBase[Dict],
    summary="Get sync schedule"
)
async def get_sync_schedule() -> IGetResponseBase[Dict]:
    """
    Получает информацию о расписании синхронизации.
    
    Returns:
        IGetResponseBase[Dict]: Расписание синхронизации
    """
    try:
        schedule_info = get_sync_schedule_info()
        return IGetResponseBase(data=schedule_info)
        
    except Exception as e:
        logger.error(f"Error getting sync schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting sync schedule: {str(e)}"
        )


@router.get(
    "/health",
    response_description="Get sync system health status",
    response_model=IGetResponseBase[Dict],
    summary="Get sync health"
)
async def get_sync_health(
    redis_client: Redis = Depends(get_redis_client)
) -> IGetResponseBase[Dict]:
    """
    Проверяет здоровье системы синхронизации.
    
    Returns:
        IGetResponseBase[Dict]: Статус здоровья
    """
    try:
        # Проверяем подключение к Redis
        ping_result = await redis_client.ping()
        
        # Получаем количество ключей
        keys_count = len(await redis_client.keys("*"))
        
        # Получаем информацию о Redis
        redis_info = await redis_client.info()
        
        health_status = {
            "status": "healthy" if ping_result else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "redis_connection": "ok" if ping_result else "failed",
                "redis_keys_count": keys_count,
                "redis_version": redis_info.get("redis_version"),
                "connected_clients": redis_info.get("connected_clients"),
                "used_memory_human": redis_info.get("used_memory_human")
            }
        }
        
        return IGetResponseBase(data=health_status)
        
    except Exception as e:
        logger.error(f"Error checking sync health: {e}")
        health_status = {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "checks": {
                "redis_connection": "failed",
                "error_message": str(e)
            }
        }
        return IGetResponseBase(data=health_status)


@router.get(
    "/stats",
    response_description="Get detailed sync statistics",
    response_model=IGetResponseBase[Dict],
    summary="Get sync statistics"
)
async def get_sync_statistics(
    redis_client: Redis = Depends(get_redis_client)
) -> IGetResponseBase[Dict]:
    """
    Получает детальную статистику синхронизации.
    
    Returns:
        IGetResponseBase[Dict]: Статистика синхронизации
    """
    try:
        # Получаем сводку
        summary = await get_balance_sync_summary()
        
        # Получаем дополнительную информацию о Redis
        redis_info = await redis_client.info()
        
        # Получаем все ключи балансов
        balance_keys = await redis_client.keys("*")
        balance_keys = [key for key in balance_keys if key.isdigit()]
        
        # Получаем значения балансов
        if balance_keys:
            balance_values = await redis_client.mget(balance_keys)
            total_balance = sum(float(val) for val in balance_values if val is not None)
            avg_balance = total_balance / len(balance_values) if balance_values else 0
        else:
            total_balance = 0
            avg_balance = 0
        
        statistics = {
            **summary,
            "balance_statistics": {
                "total_users_with_balance": len(balance_keys),
                "total_balance_amount": total_balance,
                "average_balance": avg_balance,
                "balance_keys_sample": balance_keys[:10] if balance_keys else []
            },
            "redis_statistics": {
                "total_keys": len(await redis_client.keys("*")),
                "balance_keys": len(balance_keys),
                "redis_version": redis_info.get("redis_version"),
                "connected_clients": redis_info.get("connected_clients"),
                "used_memory_human": redis_info.get("used_memory_human"),
                "uptime_in_seconds": redis_info.get("uptime_in_seconds")
            }
        }
        
        return IGetResponseBase(data=statistics)
        
    except Exception as e:
        logger.error(f"Error getting sync statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting sync statistics: {str(e)}"
        )


@router.delete(
    "/clear-cache",
    response_description="Clear sync cache and statistics",
    response_model=IGetResponseBase[Dict],
    summary="Clear sync cache"
)
async def clear_sync_cache(
    redis_client: Redis = Depends(get_redis_client)
) -> IGetResponseBase[Dict]:
    """
    Очищает кэш синхронизации и статистику.
    
    Returns:
        IGetResponseBase[Dict]: Результат очистки
    """
    try:
        # Ключи для очистки
        keys_to_delete = [
            "balance_sync:last_sync",
            "balance_sync:last_stats"
        ]
        
        # Удаляем ключи
        deleted_count = await redis_client.delete(*keys_to_delete)
        
        result = {
            "status": "success",
            "deleted_keys": deleted_count,
            "message": "Sync cache cleared successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Sync cache cleared: {deleted_count} keys deleted")
        return IGetResponseBase(data=result)
        
    except Exception as e:
        logger.error(f"Error clearing sync cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing sync cache: {str(e)}"
        ) 