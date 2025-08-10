"""
Сервис для управления ежедневным заработком пользователей.
"""

import asyncio
from datetime import datetime, date, timedelta
from typing import Optional, List, Tuple
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.models.daily_earning import DailyEarning, EarningPartition, EarningHistory
from src.models.user import User
from src.utils.currency_LUNA_to_USDT import get_luna_price_binance
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DailyEarningService:
    """Сервис для управления ежедневным заработком."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_or_create_daily_earning(self, user_id: int, earning_date: date) -> DailyEarning:
        """Получить или создать запись ежедневного заработка."""
        # Ищем существующую запись
        stmt = select(DailyEarning).where(
            and_(
                DailyEarning.user_id == user_id,
                DailyEarning.earning_date == earning_date
            )
        )
        result = await self.session.execute(stmt)
        daily_earning = result.scalar_one_or_none()
        
        if daily_earning is None:
            # Создаем новую запись
            daily_earning = DailyEarning(
                user_id=user_id,
                earning_date=earning_date,
                max_partitions=settings.EARNING_PARTITIONS_COUNT
            )
            self.session.add(daily_earning)
            await self.session.commit()
            await self.session.refresh(daily_earning)
            logger.info(f"Created new daily earning record for user {user_id} on {earning_date}")
        
        return daily_earning
    
    async def get_or_create_partition(
        self, 
        user_id: int, 
        daily_earning_id: int, 
        partition_number: int, 
        partition_date: date
    ) -> EarningPartition:
        """Получить или создать партицию заработка."""
        # Ищем существующую партицию
        stmt = select(EarningPartition).where(
            and_(
                EarningPartition.user_id == user_id,
                EarningPartition.daily_earning_id == daily_earning_id,
                EarningPartition.partition_number == partition_number,
                EarningPartition.partition_date == partition_date
            )
        )
        result = await self.session.execute(stmt)
        partition = result.scalar_one_or_none()
        
        if partition is None:
            # Создаем новую партицию
            partition = EarningPartition(
                user_id=user_id,
                daily_earning_id=daily_earning_id,
                partition_number=partition_number,
                partition_date=partition_date,
                max_clicks=settings.MAX_CLICKS_PER_PARTITION
            )
            self.session.add(partition)
            await self.session.commit()
            await self.session.refresh(partition)
            logger.info(f"Created new partition {partition_number} for user {user_id}")
        
        return partition
    
    def calculate_current_partition(self, current_time: datetime) -> int:
        """Вычислить текущую партицию на основе времени."""
        # Партиции сменяются каждые 4 часа (14400 секунд)
        seconds_since_midnight = current_time.hour * 3600 + current_time.minute * 60 + current_time.second
        partition_number = (seconds_since_midnight // settings.SECONDS_PER_PARTITION) + 1
        
        # Ограничиваем количество партиций
        return min(partition_number, settings.EARNING_PARTITIONS_COUNT)
    
    def calculate_partition_start_time(self, partition_number: int, date_obj: date) -> datetime:
        """Вычислить время начала партиции."""
        start_seconds = (partition_number - 1) * settings.SECONDS_PER_PARTITION
        start_hour = start_seconds // 3600
        start_minute = (start_seconds % 3600) // 60
        
        return datetime.combine(date_obj, datetime.min.time().replace(hour=start_hour, minute=start_minute))
    
    def calculate_partition_end_time(self, partition_number: int, date_obj: date) -> datetime:
        """Вычислить время окончания партиции."""
        end_seconds = partition_number * settings.SECONDS_PER_PARTITION
        end_hour = end_seconds // 3600
        end_minute = (end_seconds % 3600) // 60
        
        return datetime.combine(date_obj, datetime.min.time().replace(hour=end_hour, minute=end_minute))
    
    async def can_user_earn_in_partition(
        self, 
        user_id: int, 
        partition_number: int, 
        partition_date: date
    ) -> Tuple[bool, str]:
        """Проверить, может ли пользователь зарабатывать в партиции."""
        # Получаем партицию
        stmt = select(EarningPartition).where(
            and_(
                EarningPartition.user_id == user_id,
                EarningPartition.partition_number == partition_number,
                EarningPartition.partition_date == partition_date
            )
        )
        result = await self.session.execute(stmt)
        partition = result.scalar_one_or_none()
        
        if partition is None:
            return True, "Partition not found, will be created"
        
        # Проверяем, заполнена ли партиция
        if partition.is_partition_full:
            return False, f"Partition {partition_number} is full"
        
        # Проверяем количество кликов
        if partition.clicks_count >= partition.max_clicks:
            return False, f"Partition {partition_number} reached max clicks"
        
        # Проверяем лимит заработка в партиции
        if partition.earned_usd >= settings.EARNING_PER_PARTITION_USD:
            return False, f"Partition {partition_number} reached earning limit"
        
        return True, "Can earn in partition"
    
    async def process_click_earning(
        self, 
        user_id: int, 
        energy_consumed: int, 
        luna_price: float
    ) -> Tuple[bool, float, int, str]:
        """Обработать заработок за клик."""
        current_time = datetime.utcnow()
        current_date = current_time.date()
        
        # Получаем или создаем запись ежедневного заработка
        daily_earning = await self.get_or_create_daily_earning(user_id, current_date)
        
        # Проверяем дневной лимит
        if daily_earning.is_daily_limit_reached:
            return False, 0.0, 0, "Daily earning limit reached"
        
        # Вычисляем текущую партицию
        current_partition_number = self.calculate_current_partition(current_time)
        
        # Проверяем, может ли пользователь зарабатывать в партиции
        can_earn, message = await self.can_user_earn_in_partition(
            user_id, current_partition_number, current_date
        )
        
        if not can_earn:
            return False, 0.0, 0, message
        
        # Получаем или создаем партицию
        partition = await self.get_or_create_partition(
            user_id, daily_earning.id, current_partition_number, current_date
        )
        
        # Вычисляем заработок за клик (примерная формула)
        # Можно настроить более сложную логику
        base_earning_per_click = 0.01  # $0.01 за клик
        energy_multiplier = min(energy_consumed / 100, 2.0)  # Множитель от энергии
        earned_usd = base_earning_per_click * energy_multiplier
        
        # Проверяем лимит партиции
        if partition.earned_usd + earned_usd > settings.EARNING_PER_PARTITION_USD:
            earned_usd = max(0, settings.EARNING_PER_PARTITION_USD - partition.earned_usd)
        
        # Проверяем дневной лимит
        if daily_earning.total_earned_usd + earned_usd > settings.DAILY_EARNING_LIMIT_USD:
            earned_usd = max(0, settings.DAILY_EARNING_LIMIT_USD - daily_earning.total_earned_usd)
        
        if earned_usd <= 0:
            return False, 0.0, 0, "No earnings possible due to limits"
        
        # Конвертируем в LUNA
        earned_luna = int((earned_usd / luna_price) * 1000000)  # В микро-единицах
        
        # Обновляем партицию
        partition.earned_usd += earned_usd
        partition.earned_luna += earned_luna
        partition.clicks_count += 1
        
        # Проверяем, заполнена ли партиция
        if (partition.clicks_count >= partition.max_clicks or 
            partition.earned_usd >= settings.EARNING_PER_PARTITION_USD):
            partition.is_partition_full = True
            partition.partition_end_time = current_time
        
        # Обновляем ежедневный заработок
        daily_earning.total_earned_usd += earned_usd
        daily_earning.total_earned_luna += earned_luna
        daily_earning.updated_at = current_time
        
        # Проверяем дневной лимит
        if daily_earning.total_earned_usd >= settings.DAILY_EARNING_LIMIT_USD:
            daily_earning.is_daily_limit_reached = True
        
        # Создаем запись в истории
        earning_history = EarningHistory(
            user_id=user_id,
            daily_earning_id=daily_earning.id,
            partition_id=partition.id,
            click_timestamp=current_time,
            earned_usd=earned_usd,
            earned_luna=earned_luna,
            luna_price_at_click=luna_price,
            energy_consumed=energy_consumed
        )
        self.session.add(earning_history)
        
        # Обновляем баланс пользователя
        user_stmt = select(User).where(User.id == user_id)
        user_result = await self.session.execute(user_stmt)
        user = user_result.scalar_one()
        user.balance += earned_luna
        
        await self.session.commit()
        
        logger.info(f"User {user_id} earned ${earned_usd:.4f} ({earned_luna} LUNA) in partition {current_partition_number}")
        
        return True, earned_usd, earned_luna, "Earning processed successfully"
    
    async def get_daily_earning_status(self, user_id: int, target_date: date = None) -> dict:
        """Получить статус ежедневного заработка пользователя."""
        if target_date is None:
            target_date = datetime.utcnow().date()
        
        # Получаем запись ежедневного заработка
        stmt = select(DailyEarning).where(
            and_(
                DailyEarning.user_id == user_id,
                DailyEarning.earning_date == target_date
            )
        )
        result = await self.session.execute(stmt)
        daily_earning = result.scalar_one_or_none()
        
        if daily_earning is None:
            # Возвращаем пустой статус
            return {
                "user_id": user_id,
                "earning_date": target_date,
                "total_earned_usd": 0.0,
                "total_earned_luna": 0,
                "daily_limit_usd": settings.DAILY_EARNING_LIMIT_USD,
                "remaining_usd": settings.DAILY_EARNING_LIMIT_USD,
                "partitions_used": 0,
                "max_partitions": settings.EARNING_PARTITIONS_COUNT,
                "is_daily_limit_reached": False,
                "current_partition": self.calculate_current_partition(datetime.utcnow()),
                "current_partition_earned_usd": 0.0,
                "current_partition_clicks": 0,
                "current_partition_max_clicks": settings.MAX_CLICKS_PER_PARTITION,
                "next_partition_reset_time": None,
                "last_click_time": None
            }
        
        # Получаем текущую партицию
        current_time = datetime.utcnow()
        current_partition_number = self.calculate_current_partition(current_time)
        
        # Получаем информацию о текущей партиции
        partition_stmt = select(EarningPartition).where(
            and_(
                EarningPartition.user_id == user_id,
                EarningPartition.daily_earning_id == daily_earning.id,
                EarningPartition.partition_number == current_partition_number
            )
        )
        partition_result = await self.session.execute(partition_stmt)
        current_partition = partition_result.scalar_one_or_none()
        
        # Получаем последний клик
        last_click_stmt = select(EarningHistory).where(
            EarningHistory.user_id == user_id
        ).order_by(EarningHistory.click_timestamp.desc()).limit(1)
        last_click_result = await self.session.execute(last_click_stmt)
        last_click = last_click_result.scalar_one_or_none()
        
        # Вычисляем время следующего сброса партиции
        partition_end_time = self.calculate_partition_end_time(current_partition_number, target_date)
        next_reset_time = partition_end_time if current_time < partition_end_time else None
        
        return {
            "user_id": user_id,
            "earning_date": target_date,
            "total_earned_usd": daily_earning.total_earned_usd,
            "total_earned_luna": daily_earning.total_earned_luna,
            "daily_limit_usd": settings.DAILY_EARNING_LIMIT_USD,
            "remaining_usd": max(0, settings.DAILY_EARNING_LIMIT_USD - daily_earning.total_earned_usd),
            "partitions_used": daily_earning.partitions_used,
            "max_partitions": daily_earning.max_partitions,
            "is_daily_limit_reached": daily_earning.is_daily_limit_reached,
            "current_partition": current_partition_number,
            "current_partition_earned_usd": current_partition.earned_usd if current_partition else 0.0,
            "current_partition_clicks": current_partition.clicks_count if current_partition else 0,
            "current_partition_max_clicks": settings.MAX_CLICKS_PER_PARTITION,
            "next_partition_reset_time": next_reset_time,
            "last_click_time": last_click.click_timestamp if last_click else None
        }
    
    async def reset_partition(self, user_id: int, partition_number: int) -> Tuple[bool, str]:
        """Сбросить партицию (административная функция)."""
        current_date = datetime.utcnow().date()
        
        # Находим партицию
        stmt = select(EarningPartition).where(
            and_(
                EarningPartition.user_id == user_id,
                EarningPartition.partition_number == partition_number,
                EarningPartition.partition_date == current_date
            )
        )
        result = await self.session.execute(stmt)
        partition = result.scalar_one_or_none()
        
        if partition is None:
            return False, f"Partition {partition_number} not found"
        
        # Сбрасываем партицию
        partition.earned_usd = 0.0
        partition.earned_luna = 0
        partition.clicks_count = 0
        partition.is_partition_full = False
        partition.partition_start_time = datetime.utcnow()
        partition.partition_end_time = None
        partition.updated_at = datetime.utcnow()
        
        await self.session.commit()
        
        logger.info(f"Reset partition {partition_number} for user {user_id}")
        return True, f"Partition {partition_number} reset successfully"
    
    async def get_daily_earning_summary(self, user_id: int, target_date: date = None) -> dict:
        """Получить сводку ежедневного заработка."""
        if target_date is None:
            target_date = datetime.utcnow().date()
        
        # Получаем статус
        status = await self.get_daily_earning_status(user_id, target_date)
        
        # Получаем все партиции за день
        stmt = select(EarningPartition).where(
            and_(
                EarningPartition.user_id == user_id,
                EarningPartition.partition_date == target_date
            )
        ).order_by(EarningPartition.partition_number)
        result = await self.session.execute(stmt)
        partitions = result.scalars().all()
        
        # Формируем статусы партиций
        partition_statuses = []
        for partition in partitions:
            partition_status = {
                "partition_number": partition.partition_number,
                "earned_usd": partition.earned_usd,
                "earned_luna": partition.earned_luna,
                "clicks_count": partition.clicks_count,
                "max_clicks": partition.max_clicks,
                "is_partition_full": partition.is_partition_full,
                "partition_start_time": partition.partition_start_time,
                "partition_end_time": partition.partition_end_time,
                "time_until_reset": None  # Можно вычислить если нужно
            }
            partition_statuses.append(partition_status)
        
        # Вычисляем общую статистику
        total_clicks = sum(p["clicks_count"] for p in partition_statuses)
        average_earnings = status["total_earned_usd"] / total_clicks if total_clicks > 0 else 0
        
        return {
            **status,
            "partitions": partition_statuses,
            "total_clicks_today": total_clicks,
            "average_earnings_per_click": average_earnings
        } 