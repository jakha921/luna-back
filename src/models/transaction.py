from datetime import datetime

from sqlmodel import Field, Relationship

from src.models.base_model import BaseModel
from src.models.user import User


class Transaction(BaseModel, table=True):
    """
    Модель для таблицы `transactions`.

    Таблица:
    - id          int [pk, increment] - Уникальный идентификатор
    - user_id     int [ref: > users.id] - ID пользователя, связанного с транзакцией
    - amount      int - Сумма транзакции (в минимальных единицах)
    - commission  int - Комиссия за транзакцию (в минимальных единицах)
    - type        enum('withdrawal', 'referral_reward', 'income') - Тип транзакции
    - status      enum('pending', 'completed', 'failed') - Статус транзакции
    - timestamp   datetime - Дата и время транзакции
    """

    __tablename__ = "transactions"

    user_id: int = Field(foreign_key="users.id", description="ID of the user associated with the transaction")
    amount: int = Field(..., description="Transaction amount (in minimal units, positive or negative)")
    commission: int = Field(default=0, description="Transaction commission (in minimal units)")
    type: str = Field(
        ...,
        description="Type of the transaction (withdrawal, referral_reward, income)",
    )
    status: str = Field(
        default="pending",
        description="Status of the transaction (pending, completed, failed)",
    )
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of the transaction")

    # Relationships
    user: User = Relationship(back_populates="transactions")

    def __repr__(self):
        return (
            f"<Transaction id={self.id} user_id={self.user_id} amount={self.amount} "
            f"commission={self.commission} type={self.type} status={self.status}>"
        )
