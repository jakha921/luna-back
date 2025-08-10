#!/usr/bin/env python3
"""
Простой скрипт для заполнения базы данных тестовыми данными.
Запуск: docker-compose exec app python scripts/seed_simple.py
"""

import asyncio
import random
import uuid
from datetime import datetime, timedelta
import sys
import os

# Добавляем путь к src в PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.db.session import get_session
from src.models.user import User
from src.models.transaction import Transaction
from src.models.withdrawal_queue import WithdrawalQueue
from src.schemas.user import SUserCreate

# Реалистичные данные
FIRST_NAMES = ["Александр", "Дмитрий", "Михаил", "Андрей", "Сергей", "Владимир", "Алексей", "Артем", "Игорь", "Роман"]
LAST_NAMES = ["Иванов", "Петров", "Сидоров", "Смирнов", "Кузнецов", "Попов", "Васильев", "Соколов", "Михайлов", "Новиков"]
USERNAMES = ["alex", "dmitry", "mike", "andrey", "sergey", "vlad", "alexey", "artem", "igor", "roman"]

async def create_users(session, count=20):
    """Создает пользователей с уникальными referral_code"""
    users = []
    print(f"Создание {count} пользователей...")
    
    for i in range(count):
        # Генерируем уникальный referral_code
        referral_code = str(uuid.uuid4())[:8]
        
        user_data = {
            "telegram_id": 200000000 + i,
            "username": f"{random.choice(USERNAMES)}{i}",
            "firstname": random.choice(FIRST_NAMES),
            "lastname": random.choice(LAST_NAMES),
            "balance": random.randint(0, 1000000),
            "lang_code": random.choice(["ru", "en", "uz"]),
            "is_subscribed": random.choice([True, False]),
            "is_premium": random.choice([True, False]),
            "referral_code": referral_code,
            "invited_by": None
        }
        
        try:
            user_create = SUserCreate(**user_data)
            user = User(**user_create.model_dump())
            session.add(user)
            await session.flush()
            users.append(user)
            print(f"Создан пользователь: {user.username} (ID: {user.id})")
        except Exception as e:
            print(f"Ошибка создания пользователя {i}: {e}")
            continue
    
    await session.commit()
    print(f"Создано {len(users)} пользователей")
    return users

async def create_transactions(session, users, count_per_user=5):
    """Создает транзакции"""
    print(f"Создание транзакций (по {count_per_user} на пользователя)...")
    
    transaction_types = ["withdrawal", "referral_reward", "income"]
    
    for user in users:
        for _ in range(count_per_user):
            transaction = Transaction(
                user_id=user.id,
                amount=random.randint(100, 10000),
                type=random.choice(transaction_types),
                status=random.choice(["pending", "completed", "failed"]),
                timestamp=datetime.now() - timedelta(days=random.randint(0, 30))
            )
            session.add(transaction)
    
    await session.commit()
    print(f"Создано {len(users) * count_per_user} транзакций")

async def create_withdrawals(session, users, count=30):
    """Создает запросы на вывод"""
    print(f"Создание {count} запросов на вывод...")
    
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
    print(f"Создано {count} запросов на вывод")

async def main():
    """Основная функция"""
    print("🚀 Начинаем заполнение базы данных...")
    
    session = await anext(get_session())
    
    try:
        # Создаем пользователей
        users = await create_users(session, 20)
        
        if not users:
            print("❌ Не удалось создать пользователей")
            return
        
        # Создаем транзакции
        await create_transactions(session, users, 5)
        
        # Создаем запросы на вывод
        await create_withdrawals(session, users, 30)
        
        print("✅ База данных успешно заполнена!")
        print(f"📊 Статистика:")
        print(f"   👥 Пользователей: {len(users)}")
        print(f"   💰 Транзакций: {len(users) * 5}")
        print(f"   🏦 Запросов на вывод: 30")
        
    except Exception as e:
        print(f"❌ Ошибка при заполнении базы данных: {e}")
        raise
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(main())
