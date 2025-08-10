#!/usr/bin/env python3
"""
Скрипт для заполнения базы данных реалистичными тестовыми данными.
Запуск: python scripts/seed_data.py
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Optional
import sys
import os

# Добавляем путь к src в PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.db.session import get_session
from src.models.user import User
from src.models.transaction import Transaction
from src.models.withdrawal_queue import WithdrawalQueue
from src.models.daily_earning import DailyEarning, EarningPartition, EarningHistory
from src.repositories.user import UserRepository
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Реалистичные данные для генерации
FIRST_NAMES = [
    "Александр", "Дмитрий", "Михаил", "Андрей", "Сергей", "Владимир", "Артем", "Илья",
    "Максим", "Никита", "Даниил", "Егор", "Кирилл", "Роман", "Павел", "Владислав",
    "Константин", "Тимур", "Арсений", "Денис", "Анна", "Мария", "Елена", "Ольга",
    "Татьяна", "Наталья", "Ирина", "Светлана", "Екатерина", "Юлия", "Ангелина",
    "Виктория", "Полина", "Алиса", "Ксения", "Дарья", "Арина", "Валерия", "Диана"
]

LAST_NAMES = [
    "Иванов", "Смирнов", "Кузнецов", "Попов", "Васильев", "Петров", "Соколов",
    "Михайлов", "Новиков", "Федоров", "Морозов", "Волков", "Алексеев", "Лебедев",
    "Семенов", "Егоров", "Павлов", "Козлов", "Степанов", "Николаев", "Орлов",
    "Андреев", "Макаров", "Никитин", "Захаров", "Зайцев", "Соловьев", "Борисов",
    "Яковлев", "Григорьев", "Романов", "Воробьев", "Сергеев", "Кузьмин", "Фролов",
    "Александров", "Дмитриев", "Королев", "Гусев", "Киселев", "Ильин", "Максимов"
]

USERNAMES = [
    "alex_dev", "mike_coder", "anna_tech", "dmitry_ai", "maria_web", "sergey_data",
    "elena_cloud", "andrey_ml", "olga_qa", "vladimir_ops", "artem_frontend",
    "ilya_backend", "max_fullstack", "nikita_mobile", "daniel_devops", "egor_ui",
    "kirill_architect", "roman_lead", "pavel_senior", "vladislav_junior",
    "kostya_tech_lead", "timur_developer", "arseniy_coder", "denis_programmer",
    "angelina_designer", "victoria_analyst", "polina_tester", "alice_engineer",
    "ksenia_consultant", "daria_manager", "arina_coordinator", "valeria_specialist"
]

LANGUAGES = ["ru", "en", "uz"]
WALLET_ADDRESSES = [
    "0:83e127b0cbdcd5e039337ee09b9be31530799896bdfb234475d65005badc0eb9",
    "0:715fc4d527b5fa05fab2e88dc2771f284a3c87c6838f03e7b5fd0ef641f848e6",
    "0:a06b41d1a67c8eedaf79fe4ba3777696e948528fc0bf5a6f9ae2658feffccadf",
    "0:8e566a99e2663c5f2d102a1eb87a961a202e8aba88269efa89a02fe403d6fdca",
    "0:7e9a04c66bf3efe8ab8f52450760aca1188ca46080b9af985cdb04bb34133d1c"
]

TRANSACTION_TYPES = ["withdrawal", "referral_reward", "income"]
TRANSACTION_STATUSES = ["pending", "completed", "failed"]
WITHDRAWAL_STATUSES = ["pending", "approved", "rejected"]


class DataSeeder:
    def __init__(self):
        self.users: List[User] = []
        self.transactions: List[Transaction] = []
        self.withdrawals: List[WithdrawalQueue] = []
        self.daily_earnings: List[DailyEarning] = []
        self.earning_partitions: List[EarningPartition] = []
        self.earning_history: List[EarningHistory] = []

    async def seed_users(self, count: int = 100):
        """Создает реалистичных пользователей"""
        logger.info(f"Создание {count} пользователей...")
        
        session = await anext(get_session())
        user_repo = UserRepository(db=session)
        
        for i in range(count):
            # Генерируем реалистичные данные
            telegram_id = 100000000 + i
            username = random.choice(USERNAMES) + str(random.randint(1, 999))
            firstname = random.choice(FIRST_NAMES)
            lastname = random.choice(LAST_NAMES)
            balance = random.randint(0, 100000000)  # 0-100 LUNA
            wallet = random.choice(WALLET_ADDRESSES) if random.random() > 0.3 else None
            is_subscribed = random.random() > 0.2  # 80% подписаны
            lang_code = random.choice(LANGUAGES)
            is_premium = random.random() > 0.8  # 20% премиум
            registration_date = datetime.now() - timedelta(days=random.randint(1, 365))
            sync_at = registration_date + timedelta(hours=random.randint(1, 24))
            
            # Создаем пользователя
            user_data = {
                "telegram_id": telegram_id,
                "username": username,
                "firstname": firstname,
                "lastname": lastname,
                "balance": balance,
                "wallet": wallet,
                "is_subscribed": is_subscribed,
                "lang_code": lang_code,
                "is_premium": is_premium,
                "registration_date": registration_date,
                "sync_at": sync_at
            }
            
            try:
                # Создаем объект SUserCreate из словаря
                from src.schemas.user import SUserCreate
                user_create = SUserCreate(**user_data)
                user = await user_repo.create(user_create)
                self.users.append(user)
                logger.debug(f"Создан пользователь: {user.username} (ID: {user.id})")
            except Exception as e:
                logger.error(f"Ошибка создания пользователя {i}: {e}")
                continue
        
        await session.close()
        logger.info(f"Создано {len(self.users)} пользователей")

    async def seed_referrals(self):
        """Создает реферальные связи между пользователями"""
        logger.info("Создание реферальных связей...")
        
        session = await anext(get_session())
        
        # Выбираем 30% пользователей как рефералов
        referrers = random.sample(self.users, len(self.users) // 3)
        remaining_users = [u for u in self.users if u not in referrers]
        
        for user in remaining_users:
            if random.random() > 0.7:  # 30% пользователей имеют рефералов
                referrer = random.choice(referrers)
                user.referred_by = referrer.id
                user.invitation_bonus = random.randint(1000000, 5000000)  # 1-5 LUNA
                session.add(user)
        
        await session.commit()
        await session.close()
        logger.info("Реферальные связи созданы")

    async def seed_transactions(self, count_per_user: int = 5):
        """Создает транзакции для пользователей"""
        logger.info(f"Создание транзакций (по {count_per_user} на пользователя)...")
        
        session = await anext(get_session())
        
        for user in self.users:
            for _ in range(count_per_user):
                transaction_type = random.choice(TRANSACTION_TYPES)
                status = random.choice(TRANSACTION_STATUSES)
                
                # Генерируем реалистичные суммы в зависимости от типа
                if transaction_type == "withdrawal":
                    amount = random.randint(1000000, 10000000)  # 1-10 LUNA
                    commission = amount // 100  # 1% комиссия
                elif transaction_type == "referral_reward":
                    amount = random.randint(500000, 2000000)  # 0.5-2 LUNA
                    commission = 0
                else:  # income
                    amount = random.randint(10000, 500000)  # 0.01-0.5 LUNA
                    commission = 0
                
                timestamp = datetime.now() - timedelta(
                    days=random.randint(1, 30),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
                
                transaction = Transaction(
                    user_id=user.id,
                    amount=amount,
                    commission=commission,
                    type=transaction_type,
                    status=status,
                    timestamp=timestamp
                )
                
                session.add(transaction)
                self.transactions.append(transaction)
        
        await session.commit()
        await session.close()
        logger.info(f"Создано {len(self.transactions)} транзакций")

    async def seed_withdrawals(self, count: int = 20):
        """Создает запросы на вывод средств"""
        logger.info(f"Создание {count} запросов на вывод...")
        
        session = await anext(get_session())
        
        for _ in range(count):
            user = random.choice(self.users)
            amount = random.randint(1000000, 5000000)  # 1-5 LUNA
            status = random.choice(WITHDRAWAL_STATUSES)
            
            withdrawal = WithdrawalQueue(
                user_id=user.id,
                amount=amount,
                status=status
            )
            
            session.add(withdrawal)
            self.withdrawals.append(withdrawal)
        
        await session.commit()
        await session.close()
        logger.info(f"Создано {len(self.withdrawals)} запросов на вывод")

    async def seed_daily_earnings(self):
        """Создает данные о ежедневных заработках"""
        logger.info("Создание данных о ежедневных заработках...")
        
        session = await anext(get_session())
        
        # Создаем данные за последние 30 дней
        for user in random.sample(self.users, len(self.users) // 2):  # 50% пользователей
            for days_ago in range(30):
                date = datetime.now().date() - timedelta(days=days_ago)
                
                # Генерируем реалистичные данные заработка
                total_earned_usd = random.uniform(0, 30)  # 0-30 USD
                total_earned_luna = int(total_earned_usd * 1000000 / 0.16)  # Примерный курс
                partitions_used = random.randint(0, 6)
                is_daily_limit_reached = total_earned_usd >= 30
                
                daily_earning = DailyEarning(
                    user_id=user.id,
                    earning_date=date,
                    total_earned_usd=total_earned_usd,
                    total_earned_luna=total_earned_luna,
                    partitions_used=partitions_used,
                    is_daily_limit_reached=is_daily_limit_reached,
                    last_partition_reset=datetime.now() - timedelta(hours=random.randint(1, 24))
                )
                
                session.add(daily_earning)
                self.daily_earnings.append(daily_earning)
        
        await session.commit()
        await session.close()
        logger.info(f"Создано {len(self.daily_earnings)} записей о ежедневных заработках")

    async def run(self, user_count: int = 100):
        """Запускает полное заполнение базы данных"""
        logger.info("Начинаем заполнение базы данных...")
        
        try:
            await self.seed_users(user_count)
            await self.seed_referrals()
            await self.seed_transactions()
            await self.seed_withdrawals()
            await self.seed_daily_earnings()
            
            logger.info("✅ Заполнение базы данных завершено успешно!")
            logger.info(f"📊 Статистика:")
            logger.info(f"   - Пользователей: {len(self.users)}")
            logger.info(f"   - Транзакций: {len(self.transactions)}")
            logger.info(f"   - Запросов на вывод: {len(self.withdrawals)}")
            logger.info(f"   - Записей о заработках: {len(self.daily_earnings)}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при заполнении базы данных: {e}")
            raise


async def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Заполнение базы данных тестовыми данными")
    parser.add_argument("--users", type=int, default=100, help="Количество пользователей (по умолчанию: 100)")
    parser.add_argument("--clear", action="store_true", help="Очистить базу данных перед заполнением")
    
    args = parser.parse_args()
    
    seeder = DataSeeder()
    await seeder.run(args.users)


if __name__ == "__main__":
    asyncio.run(main())
