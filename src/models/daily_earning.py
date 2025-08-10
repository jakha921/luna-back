"""
Модель для отслеживания ежедневных лимитов заработка пользователей.
"""

from datetime import datetime, date
from typing import Optional
from sqlmodel import Field, SQLModel


class DailyEarning(SQLModel, table=True):
    """Модель для отслеживания ежедневных лимитов заработка."""
    
    __tablename__ = "daily_earnings"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    earning_date: date = Field(index=True)  # Дата заработка
    total_earned_usd: float = Field(default=0.0)  # Общий заработок в USD за день
    total_earned_luna: int = Field(default=0)  # Общий заработок в LUNA за день
    partitions_used: int = Field(default=0)  # Количество использованных партиций
    max_partitions: int = Field(default=6)  # Максимальное количество партиций
    is_daily_limit_reached: bool = Field(default=False)  # Достигнут ли дневной лимит
    last_partition_reset: Optional[datetime] = Field(default=None)  # Время последнего сброса партиции
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        arbitrary_types_allowed = True


class EarningPartition(SQLModel, table=True):
    """Модель для отслеживания партиций заработка."""
    
    __tablename__ = "earning_partitions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    daily_earning_id: int = Field(foreign_key="daily_earnings.id", index=True)
    partition_number: int = Field(index=True)  # Номер партиции (1-6)
    partition_date: date = Field(index=True)  # Дата партиции
    earned_usd: float = Field(default=0.0)  # Заработано USD в этой партиции
    earned_luna: int = Field(default=0)  # Заработано LUNA в этой партиции
    clicks_count: int = Field(default=0)  # Количество кликов в партиции
    max_clicks: int = Field(default=250)  # Максимальное количество кликов
    is_partition_full: bool = Field(default=False)  # Заполнена ли партиция
    partition_start_time: Optional[datetime] = Field(default=None)  # Время начала партиции
    partition_end_time: Optional[datetime] = Field(default=None)  # Время окончания партиции
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        arbitrary_types_allowed = True


class EarningHistory(SQLModel, table=True):
    """Модель для истории заработка (детальная информация о каждом клике)."""
    
    __tablename__ = "earning_history"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    daily_earning_id: int = Field(foreign_key="daily_earnings.id", index=True)
    partition_id: int = Field(foreign_key="earning_partitions.id", index=True)
    click_timestamp: datetime = Field(index=True)  # Время клика
    earned_usd: float = Field(default=0.0)  # Заработано USD за этот клик
    earned_luna: int = Field(default=0)  # Заработано LUNA за этот клик
    luna_price_at_click: float = Field(default=0.0)  # Цена LUNA на момент клика
    energy_consumed: int = Field(default=0)  # Потребленная энергия
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        arbitrary_types_allowed = True 