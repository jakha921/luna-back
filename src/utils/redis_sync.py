import logging
from typing import Dict, Optional
from redis.asyncio import Redis
from redis.exceptions import ConnectionError, RedisError

logger = logging.getLogger(__name__)


async def get_all_telegram_balances(redis_client: Redis, pattern: str = "*") -> Dict[str, str]:
    """
    Получает все балансы пользователей из Redis.
    
    Args:
        redis_client: Redis клиент
        pattern: Паттерн для поиска ключей (по умолчанию все ключи)
        
    Returns:
        Dict[str, str]: Словарь {telegram_id: balance}
        
    Raises:
        ConnectionError: Ошибка подключения к Redis
        RedisError: Другие ошибки Redis
    """
    try:
        # Получить все ключи по паттерну
        keys = await redis_client.keys(pattern)
        
        if not keys:
            logger.info("No keys found in Redis")
            return {}
            
        # Фильтровать только валидные telegram_id (числовые ключи)
        valid_keys = []
        for key in keys:
            try:
                int(key)  # Проверяем что ключ - это число
                valid_keys.append(key)
            except ValueError:
                logger.debug(f"Skipping non-numeric key: {key}")
                continue
        
        if not valid_keys:
            logger.info("No valid telegram_id keys found")
            return {}
            
        # Получить значения для всех валидных ключей одним запросом
        values = await redis_client.mget(valid_keys)
        
        # Создать словарь telegram_id: balance
        result = {}
        for key, value in zip(valid_keys, values):
            if value is not None:
                result[key] = value
            else:
                logger.warning(f"Key {key} has no value in Redis")
                
        logger.info(f"Retrieved {len(result)} balance records from Redis")
        return result
        
    except ConnectionError as e:
        logger.error(f"Redis connection error: {e}")
        raise
    except RedisError as e:
        logger.error(f"Redis error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting Redis data: {e}")
        raise RedisError(f"Unexpected error: {e}")


async def clear_synced_data(redis_client: Redis, telegram_ids: list) -> int:
    """
    Удаляет синхронизированные данные из Redis (опционально).
    
    Args:
        redis_client: Redis клиент
        telegram_ids: Список telegram_id для удаления
        
    Returns:
        int: Количество удаленных ключей
    """
    try:
        if not telegram_ids:
            return 0
            
        # Конвертируем в строки для Redis
        keys_to_delete = [str(tid) for tid in telegram_ids]
        deleted_count = await redis_client.delete(*keys_to_delete)
        
        logger.info(f"Deleted {deleted_count} keys from Redis")
        return deleted_count
        
    except RedisError as e:
        logger.error(f"Error deleting keys from Redis: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting Redis keys: {e}")
        raise RedisError(f"Unexpected error: {e}") 