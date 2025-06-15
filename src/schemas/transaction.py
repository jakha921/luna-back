from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class STransactionBase(BaseModel):
    user_id: int = Field(..., description="ID of the user associated with the transaction")
    amount: int = Field(..., description="Transaction amount (positive or negative in minimal units)")
    commission: Optional[int] = Field(0, description="Commission for the transaction (in minimal units)")
    type: str = Field(..., description="Type of the transaction (withdrawal, referral_reward, income)")
    status: Optional[str] = Field("pending", description="Status of the transaction (pending, completed, failed)")


class STransactionCreate(STransactionBase):
    pass


class STransactionUpdate(STransactionBase):
    pass


class TransactionRead(STransactionBase):
    id: int = Field(..., description="Unique transaction ID")
    timestamp: datetime = Field(..., description="Timestamp of the transaction")
    created_at: datetime = Field(..., description="Timestamp of the transaction creation")
    updated_at: Optional[datetime] = Field(None, description="Timestamp of the transaction update")
    deleted_at: Optional[datetime] = Field(None, description="Timestamp of the transaction deletion")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "user_id": 1234567890,
                "amount": 100,
                "commission": 0,
                "type": "income",
                "status": "pending",
                "id": 1234567890,
                "timestamp": "2022-01-01T00:00:00",
                "created_at": "2022-01-01T00:00:00",
                "updated_at": "2022-01-01T00:00:00",
                "deleted_at": None,
            }
        }
