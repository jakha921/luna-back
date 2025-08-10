"""
Схемы для API ежедневного заработка.
"""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field


class DailyEarningBase(BaseModel):
    """Базовая схема для ежедневного заработка."""
    user_id: int
    earning_date: date
    total_earned_usd: float = 0.0
    total_earned_luna: int = 0
    partitions_used: int = 0
    max_partitions: int = 6
    is_daily_limit_reached: bool = False


class DailyEarningCreate(DailyEarningBase):
    """Схема для создания записи ежедневного заработка."""
    pass


class DailyEarningRead(DailyEarningBase):
    """Схема для чтения записи ежедневного заработка."""
    id: int
    last_partition_reset: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class EarningPartitionBase(BaseModel):
    """Базовая схема для партиции заработка."""
    user_id: int
    daily_earning_id: int
    partition_number: int
    partition_date: date
    earned_usd: float = 0.0
    earned_luna: int = 0
    clicks_count: int = 0
    max_clicks: int = 250
    is_partition_full: bool = False


class EarningPartitionCreate(EarningPartitionBase):
    """Схема для создания партиции заработка."""
    pass


class EarningPartitionRead(EarningPartitionBase):
    """Схема для чтения партиции заработка."""
    id: int
    partition_start_time: Optional[datetime] = None
    partition_end_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class EarningHistoryBase(BaseModel):
    """Базовая схема для истории заработка."""
    user_id: int
    daily_earning_id: int
    partition_id: int
    click_timestamp: datetime
    earned_usd: float = 0.0
    earned_luna: int = 0
    luna_price_at_click: float = 0.0
    energy_consumed: int = 0


class EarningHistoryCreate(EarningHistoryBase):
    """Схема для создания записи истории заработка."""
    pass


class EarningHistoryRead(EarningHistoryBase):
    """Схема для чтения записи истории заработка."""
    id: int
    created_at: datetime


class DailyEarningStatus(BaseModel):
    """Схема статуса ежедневного заработка пользователя."""
    user_id: int
    earning_date: date
    total_earned_usd: float
    total_earned_luna: int
    daily_limit_usd: float
    remaining_usd: float
    partitions_used: int
    max_partitions: int
    is_daily_limit_reached: bool
    current_partition: Optional[int] = None
    current_partition_earned_usd: float = 0.0
    current_partition_clicks: int = 0
    current_partition_max_clicks: int = 250
    next_partition_reset_time: Optional[datetime] = None
    last_click_time: Optional[datetime] = None


class EarningPartitionStatus(BaseModel):
    """Схема статуса партиции заработка."""
    partition_number: int
    earned_usd: float
    earned_luna: int
    clicks_count: int
    max_clicks: int
    is_partition_full: bool
    partition_start_time: Optional[datetime] = None
    partition_end_time: Optional[datetime] = None
    time_until_reset: Optional[int] = None  # секунды до сброса


class DailyEarningSummary(BaseModel):
    """Схема сводки ежедневного заработка."""
    user_id: int
    earning_date: date
    total_earned_usd: float
    total_earned_luna: int
    daily_limit_usd: float
    remaining_usd: float
    partitions_used: int
    max_partitions: int
    is_daily_limit_reached: bool
    partitions: List[EarningPartitionStatus]
    total_clicks_today: int
    average_earnings_per_click: float


class ClickEarningRequest(BaseModel):
    """Схема запроса на заработок за клик."""
    user_id: int
    energy_consumed: int = Field(..., ge=1, description="Потребленная энергия")
    luna_price: float = Field(..., gt=0, description="Текущая цена LUNA")


class ClickEarningResponse(BaseModel):
    """Схема ответа на заработок за клик."""
    success: bool
    earned_usd: float
    earned_luna: int
    luna_price_at_click: float
    energy_consumed: int
    daily_earning_status: DailyEarningStatus
    message: str


class PartitionResetRequest(BaseModel):
    """Схема запроса на сброс партиции."""
    user_id: int
    partition_number: int


class PartitionResetResponse(BaseModel):
    """Схема ответа на сброс партиции."""
    success: bool
    partition_number: int
    reset_time: datetime
    message: str


class DailyEarningStats(BaseModel):
    """Схема статистики ежедневного заработка."""
    total_users_earning_today: int
    total_earned_usd_today: float
    total_earned_luna_today: int
    average_earnings_per_user: float
    users_reached_daily_limit: int
    most_active_partition: int
    total_clicks_today: int 