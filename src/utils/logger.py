import os
import sys
from loguru import logger


def init_logger():
    """
    Инициализация логера с настройками для файлового логирования.
    Настраивает различные уровни логов с ротацией и сжатием.
    Совместим с Sentry integration.
    """
    # Создать директорию для логов если не существует
    os.makedirs("logs", exist_ok=True)
    
    # НЕ удаляем все handlers - оставляем для совместимости с Sentry
    # logger.remove() - закомментировано для Sentry compatibility
    
    # Добавить консольный вывод с цветами для development
    logger.add(
        sink=sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{file}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True,
        enqueue=True,
        filter=lambda record: record["level"].no >= 20,  # INFO и выше
    )
    
    # Общий лог файл для всех сообщений
    logger.add(
        sink="logs/app.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{file}:{line} | {message}",
        rotation="30 days",
        retention="90 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True,
        catch=True,
        level="DEBUG",
    )
    
    # Отдельный файл для ошибок
    logger.add(
        sink="logs/errors.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{file}:{line} | {message}",
        rotation="30 days",
        retention="90 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True,
        catch=True,
        level="ERROR",
        filter=lambda record: record["level"].name in ["ERROR", "CRITICAL"],
    )
    
    # Файл для синхронизации Redis
    logger.add(
        sink="logs/redis_sync.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{file}:{line} | {message}",
        rotation="7 days",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True,
        catch=True,
        level="INFO",
        filter=lambda record: "redis" in record["message"].lower() or "sync" in record["message"].lower(),
    )
    
    # Файл для API запросов и производительности  
    logger.add(
        sink="logs/api.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{file}:{line} | {message}",
        rotation="7 days",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True,
        catch=True,
        level="INFO",
        filter=lambda record: any(keyword in record["name"].lower() for keyword in ["api", "router", "endpoint"]),
    )
    
    logger.success("Logger initialized successfully")


def get_logger(name: str = None):
    """
    Получить логер для конкретного модуля.
    
    Args:
        name: Имя модуля для логера
        
    Returns:
        logger: Настроенный логер
    """
    if name:
        return logger.bind(name=name)
    return logger 