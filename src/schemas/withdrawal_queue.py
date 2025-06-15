from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SWithdrawalBase(BaseModel):
    user_id: int = Field(..., description="ID of the user making the withdrawal request")
    amount: int = Field(..., gt=0, description="Amount to withdraw (in minimal units)")
    status: Optional[str] = Field("pending", description="Status of the withdrawal (pending, approved, rejected)")


class SWithdrawalCreate(SWithdrawalBase):
    pass


class SWithdrawalUpdate(SWithdrawalBase):
    pass

class SWithdrawalRead(SWithdrawalBase):
    id: int = Field(..., description="Unique withdrawal request ID")
    created_at: datetime = Field(..., description="Timestamp of the user creation")
    updated_at: datetime = Field(..., description="Timestamp of the user update")
    deleted_at: Optional[datetime] = Field(None, description="Timestamp of the user deletion")


    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "user_id": 1234567890,
                "amount": 100,
                "status": "pending",
                "id": 1234567890,
                "created_at": "2022-01-01T00:00:00",
                "updated_at": "2022-01-01T00:00:00",
                "deleted_at": None,
            }
        }
