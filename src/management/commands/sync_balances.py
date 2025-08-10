"""
Management command for manual balance synchronization.
"""

import asyncio
import click
from datetime import datetime
from typing import Optional

from src.core.config import settings
from src.db.session import get_session
from src.repositories.user import UserRepository
from src.utils.redis_sync import get_all_telegram_balances
from src.utils.logger import get_logger

logger = get_logger(__name__)


@click.command()
@click.option(
    "--force",
    is_flag=True,
    help="Force synchronization even if recently synced"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be synced without actually doing it"
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Verbose output"
)
def sync_balances(force: bool, dry_run: bool, verbose: bool):
    """
    Management command for manual balance synchronization.
    
    This command synchronizes user balances from Redis to the database.
    """
    if verbose:
        logger.setLevel("DEBUG")
    
    logger.info("Starting manual balance synchronization...")
    logger.info(f"Force sync: {force}")
    logger.info(f"Dry run: {dry_run}")
    
    try:
        # Запускаем асинхронную функцию
        result = asyncio.run(_sync_balances_async(force, dry_run))
        
        if result["status"] == "completed":
            logger.info("✅ Balance synchronization completed successfully!")
            logger.info(f"📊 Statistics: {result}")
        elif result["status"] == "completed_with_errors":
            logger.warning("⚠️ Balance synchronization completed with errors!")
            logger.warning(f"📊 Statistics: {result}")
        else:
            logger.error("❌ Balance synchronization failed!")
            logger.error(f"📊 Statistics: {result}")
            
    except Exception as e:
        logger.error(f"❌ Error during balance synchronization: {e}")
        raise click.ClickException(str(e))


async def _sync_balances_async(force: bool, dry_run: bool) -> dict:
    """
    Асинхронная функция синхронизации балансов.
    
    Args:
        force: Принудительная синхронизация
        dry_run: Показать что будет синхронизировано без выполнения
        
    Returns:
        dict: Статистика синхронизации
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
        "status": "failed",
        "dry_run": dry_run
    }
    
    try:
        # Получаем данные из Redis
        from src.utils.redis_sync import get_all_telegram_balances
        from redis.asyncio import Redis
        
        redis_client = Redis(
            host=settings.REDIS_HOST,
            port=int(settings.REDIS_PORT),
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        
        redis_data = await get_all_telegram_balances(redis_client)
        await redis_client.close()
        
        sync_stats["redis_keys_found"] = len(redis_data)
        
        if not redis_data:
            logger.info("No balance data found in Redis")
            sync_stats.update({
                "status": "completed",
                "end_time": datetime.utcnow().isoformat(),
                "sync_duration_seconds": (datetime.utcnow() - start_time).total_seconds()
            })
            return sync_stats
        
        logger.info(f"Found {len(redis_data)} balance records in Redis")
        
        if dry_run:
            logger.info("DRY RUN - Would sync the following balances:")
            for telegram_id, balance in list(redis_data.items())[:10]:  # Показываем первые 10
                logger.info(f"  User {telegram_id}: {balance}")
            if len(redis_data) > 10:
                logger.info(f"  ... and {len(redis_data) - 10} more records")
            
            sync_stats.update({
                "status": "completed",
                "end_time": datetime.utcnow().isoformat(),
                "sync_duration_seconds": (datetime.utcnow() - start_time).total_seconds()
            })
            return sync_stats
        
        # Выполняем синхронизацию
        async with get_session() as session:
            user_repo = UserRepository(db=session)
            sync_result = await user_repo.sync_balances_from_redis(redis_data)
            
            # Обновляем статистику
            sync_stats.update(sync_result)
            sync_stats["total_processed"] = len(redis_data)
            
            # Проверяем успешность синхронизации
            if sync_stats["error_count"] == 0:
                sync_stats["status"] = "completed"
                logger.info(f"✅ Successfully synced {sync_stats['updated_count']} balances")
            else:
                sync_stats["status"] = "completed_with_errors"
                logger.warning(f"⚠️ Synced with {sync_stats['error_count']} errors")
            
            sync_stats.update({
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


@click.command()
@click.option(
    "--days",
    default=7,
    help="Number of days to look back for old data"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be cleaned without actually doing it"
)
def cleanup_old_balances(days: int, dry_run: bool):
    """
    Management command for cleaning up old balance data.
    
    This command removes old balance data from Redis.
    """
    logger.info(f"Starting cleanup of balances older than {days} days...")
    logger.info(f"Dry run: {dry_run}")
    
    try:
        result = asyncio.run(_cleanup_old_balances_async(days, dry_run))
        
        if result["status"] == "completed":
            logger.info("✅ Cleanup completed successfully!")
            logger.info(f"📊 Statistics: {result}")
        else:
            logger.warning("⚠️ Cleanup completed with issues!")
            logger.warning(f"📊 Statistics: {result}")
            
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}")
        raise click.ClickException(str(e))


async def _cleanup_old_balances_async(days: int, dry_run: bool) -> dict:
    """
    Асинхронная функция очистки старых балансов.
    
    Args:
        days: Количество дней
        dry_run: Показать что будет очищено без выполнения
        
    Returns:
        dict: Статистика очистки
    """
    # TODO: Реализовать очистку старых данных
    logger.info("Cleanup functionality not yet implemented")
    
    return {
        "cleaned_keys": 0,
        "days_old": days,
        "status": "not_implemented",
        "dry_run": dry_run
    }


@click.command()
def health_check():
    """
    Management command for checking system health.
    
    This command checks the health of Redis and database connections.
    """
    logger.info("Starting system health check...")
    
    try:
        result = asyncio.run(_health_check_async())
        
        if result["status"] == "healthy":
            logger.info("✅ System is healthy!")
            logger.info(f"📊 Health status: {result}")
        else:
            logger.error("❌ System is unhealthy!")
            logger.error(f"📊 Health status: {result}")
            
    except Exception as e:
        logger.error(f"❌ Error during health check: {e}")
        raise click.ClickException(str(e))


async def _health_check_async() -> dict:
    """
    Асинхронная функция проверки здоровья системы.
    
    Returns:
        dict: Статус здоровья
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    try:
        # Проверяем подключение к Redis
        from redis.asyncio import Redis
        
        redis_client = Redis(
            host=settings.REDIS_HOST,
            port=int(settings.REDIS_PORT),
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        
        ping_result = await redis_client.ping()
        health_status["checks"]["redis"] = "ok" if ping_result else "failed"
        
        # Получаем количество ключей
        keys_count = len(await redis_client.keys("*"))
        health_status["checks"]["redis_keys_count"] = keys_count
        
        await redis_client.close()
        
        # Проверяем подключение к базе данных
        async with get_session() as session:
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


if __name__ == "__main__":
    sync_balances() 