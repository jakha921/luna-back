from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, Relationship

from src.models.base_model import BaseModel
from src.models.user import User


class WithdrawalQueue(BaseModel, table=True):
    """
    Модель для таблицы `withdrawal_queue`.

    Таблица:
    - id              int [pk, increment] - Уникальный идентификатор
    - user_id         int [ref: > users.id] - ID пользователя, подавшего запрос
    - amount          int - Сумма для вывода (в минимальных единицах)
    - status          enum('pending', 'approved', 'rejected') - Статус запроса
    """

    __tablename__ = "withdrawal_queue"

    user_id: int = Field(foreign_key="users.id", description="ID of the user making the withdrawal request")
    amount: int = Field(..., gt=0, description="Amount to withdraw (in minimal units)")
    status: str = Field(
        default="pending",
        description="Status of the withdrawal request (pending, approved, rejected)",
    )

    # Relationships
    user: User = Relationship(back_populates="withdrawal_requests")

    def __repr__(self):
        return (
            f"<WithdrawalQueue id={self.id} user_id={self.user_id} "
            f"amount={self.amount} status={self.status}>"
        )

    def __str__(self):
        return f"ID {self.id} ({self.status})"