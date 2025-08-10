#!/usr/bin/env python3
"""
Упрощенный скрипт для заполнения базы данных внутри Docker контейнера.
Запуск: docker-compose exec app python scripts/seed_docker.py
"""

import asyncio
import random
from datetime import datetime, timedelta
import sys
import os

# Добавляем путь к src в PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.db.session import get_session
from src.models.user import User
from src.models.transaction import Transaction
from src.models.withdrawal_queue import WithdrawalQueue
from src.models.daily_earning import DailyEarning
from src.schemas.user import SUserCreate
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Реалистичные данные
FIRST_NAMES = ["Александр", "Дмитрий", "Михаил", "Андрей", "Сергей", "Владимир", "Алексей", "Артем", "Игорь", "Роман"]
LAST_NAMES = ["Иванов", "Петров", "Сидоров", "Смирнов", "Кузнецов", "Попов", "Васильев", "Соколов", "Михайлов", "Новиков"]
USERNAMES = ["alex", "dmitry", "mike", "andrey", "sergey", "vlad", "alexey", "artem", "igor", "roman"]

async def create_test_users(session, count=10):
    """Создает тестовых пользователей"""
    users = []
    logger.info(f"Создание {count} пользователей...")
    
    for i in range(count):
        user_data = {
            "telegram_id": 100000000 + i,
            "username": f"{random.choice(USERNAMES)}{i}",
            "firstname": random.choice(FIRST_NAMES),
            "lastname": random.choice(LAST_NAMES),
            "balance": random.randint(0, 1000000),
            "lang_code": random.choice(["ru", "en", "uz"]),
            "is_subscribed": random.choice([True, False]),
            "is_premium": random.choice([True, False]),
            "referral_code": f"ref{random.randint(1000, 9999)}",
            "invited_by": None
        }
        
        try:
            user_create = SUserCreate(**user_data)
            user = User(**user_create.model_dump())
            session.add(user)
            await session.flush()
            users.append(user)
            logger.debug(f"Создан пользователь: {user.username}")
        except Exception as e:
            logger.error(f"Ошибка создания пользователя {i}: {e}")
            continue
    
    await session.commit()
    logger.info(f"Создано {len(users)} пользователей")
    return users

async def create_test_transactions(session, users, count_per_user=3):
    """Создает тестовые транзакции"""
    logger.info(f"Создание транзакций (по {count_per_user} на пользователя)...")
    
    transaction_types = ["deposit", "withdrawal", "bonus", "referral"]
    
    for user in users:
        for _ in range(count_per_user):
            transaction = Transaction(
                user_id=user.id,
                amount=random.randint(100, 10000),
                transaction_type=random.choice(transaction_types),
                status=random.choice(["pending", "completed", "failed"]),
                created_at=datetime.now() - timedelta(days=random.randint(0, 30))
            )
            session.add(transaction)
    
    await session.commit()
    logger.info(f"Создано {len(users) * count_per_user} транзакций")

async def create_test_withdrawals(session, users, count=20):
    """Создает тестовые запросы на вывод"""
    logger.info(f"Создание {count} запросов на вывод...")
    
    for _ in range(count):
        user = random.choice(users)
        withdrawal = WithdrawalQueue(
            user_id=user.id,
            amount=random.randint(1000, 50000),
            wallet_address=f"EQ{random.randint(1000000000000000000, 9999999999999999999)}",
            status=random.choice(["pending", "processing", "completed", "failed"]),
            created_at=datetime.now() - timedelta(days=random.randint(0, 7))
        )
        session.add(withdrawal)
    
    await session.commit()
    logger.info(f"Создано {count} запросов на вывод")

async def main():
    """Основная функция"""
    logger.info("Начинаем заполнение базы данных...")
    
    session = await anext(get_session())
    
    try:
        # Создаем пользователей
        users = await create_test_users(session, 10)
        
        if not users:
            logger.error("Не удалось создать пользователей")
            return
        
        # Создаем транзакции
        await create_test_transactions(session, users, 3)
        
        # Создаем запросы на вывод
        await create_test_withdrawals(session, users, 10)
        
        logger.info("✅ База данных успешно заполнена!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при заполнении базы данных: {e}")
        raise
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(main())
