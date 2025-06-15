from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import Column, Index
from sqlalchemy.types import BigInteger
from sqlmodel import Field, Relationship

from src.models.base_model import BaseModel


class User(BaseModel, table=True):
    """
    Модель пользователя для таблицы `users`.

    Таблица:
    - id              int [pk, increment] - Уникальный идентификатор
    - telegram_id     bigint [unique] - Telegram ID пользователя
    - username        varchar(255) - Имя пользователя Telegram (опционально)
    - balance         int - Баланс в LUNATERRA (в минимальных единицах)
    - wallet          varchar(255) - Подключённый кошелёк
    - referral_code   varchar(50) [unique] - Уникальный реферальный код
    - referred_by     int [ref: > users.id] - ID пользователя, пригласившего текущего
    - registration_date datetime - Дата регистрации
    - is_subscribed   boolean - Подписка на канал (да/нет)
    """

    __tablename__ = "users"

    telegram_id: int = Field(
        sa_column=Column(BigInteger, unique=True), description="Telegram ID"
    )
    username: Optional[str] = Field(default=None, description="Telegram username")
    firstname: Optional[str] = Field(default=None, description="First name")
    lastname: Optional[str] = Field(default=None, description="Last name")
    balance: int = Field(default=0, description="Balance in LUNATERRA (minimal units)")
    wallet: Optional[str] = Field(default=None, description="Connected wallet")
    referral_code: str = Field(default_factory=lambda: str(uuid4())[:8], unique=True,
                               description="Unique referral code")
    referred_by: Optional[int] = Field(default=None, foreign_key="users.id", description="Referral user ID")
    registration_date: datetime = Field(default_factory=datetime.now, description="Registration date")
    is_subscribed: bool = Field(default=False, description="Subscription to the channel")
    lang_code: Optional[str] = Field(default=None, description="Language code")
    is_premium: bool = Field(default=False, description="Premium user status", nullable=True)
    invitation_bonus: int = Field(default=0, description="Invitation bonus in LUNATERRA (minimal units)", nullable=True)
    sync_at: Optional[datetime] = Field(default=None, description="Last synchronization date")

    # Relationships
    referred_users: List["User"] = Relationship(
        back_populates="referrer",
        sa_relationship_kwargs={"lazy": "joined", "cascade": "all, delete-orphan"},
    )
    referrer: Optional["User"] = Relationship(
        back_populates="referred_users",
        sa_relationship_kwargs={"uselist": False, "remote_side": "User.id"},
    )
    withdrawal_requests: List["WithdrawalQueue"] = Relationship(back_populates="user")
    transactions: List["Transaction"] = Relationship(back_populates="user")

    __table_args__ = (Index("ix_users_telegram_id", "telegram_id"),)

    def __repr__(self):
        return f"<User id={self.id} telegram_id={self.telegram_id}>"

    def __str__(self):
        return f"{self.username or self.telegram_id}"
