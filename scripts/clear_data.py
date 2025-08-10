#!/usr/bin/env python3
"""
Скрипт для очистки базы данных.
Запуск: python scripts/clear_data.py
"""

import asyncio
import sys
import os

# Добавляем путь к src в PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.db.session import get_session
from src.models.user import User
from src.models.transaction import Transaction
from src.models.withdrawal_queue import WithdrawalQueue
from src.models.daily_earning import DailyEarning, EarningPartition, EarningHistory
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def clear_database():
    """Очищает все таблицы в базе данных"""
    logger.info("Начинаем очистку базы данных...")
    
    session = await anext(get_session())
    
    try:
        # Очищаем таблицы в правильном порядке (с учетом внешних ключей)
        logger.info("Очистка таблицы earning_history...")
        await session.execute("DELETE FROM earning_history")
        
        logger.info("Очистка таблицы earning_partitions...")
        await session.execute("DELETE FROM earning_partitions")
        
        logger.info("Очистка таблицы daily_earnings...")
        await session.execute("DELETE FROM daily_earnings")
        
        logger.info("Очистка таблицы withdrawal_queue...")
        await session.execute("DELETE FROM withdrawal_queue")
        
        logger.info("Очистка таблицы transactions...")
        await session.execute("DELETE FROM transactions")
        
        logger.info("Очистка таблицы users...")
        await session.execute("DELETE FROM users")
        
        await session.commit()
        logger.info("✅ База данных очищена успешно!")
        
    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка при очистке базы данных: {e}")
        raise
    finally:
        await session.close()


async def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Очистка базы данных")
    parser.add_argument("--confirm", action="store_true", help="Подтвердить очистку")
    
    args = parser.parse_args()
    
    if not args.confirm:
        print("⚠️  ВНИМАНИЕ: Этот скрипт удалит ВСЕ данные из базы!")
        print("Для подтверждения используйте флаг --confirm")
        return
    
    await clear_database()


if __name__ == "__main__":
    asyncio.run(main())
