from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, validator

class SSyncBalance(BaseModel):
    balance: float = Field(..., description="Balance in LUNATERRA (minimal units)")
    value: float = Field(..., description="Value in LUNATERRA")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "balance": 0,
                "value": 0,
            }
        }

class SGetSyncBalance(SSyncBalance):
    balance: int = Field(..., description="Balance in LUNATERRA (minimal units)")
    sync_at: datetime = Field(..., description="Last synchronization date")
    seconds_recharge: int = Field(0, description="Seconds to recharge")
    charge_per_second: float = Field(0, description="Charge per second")
    # charge_energy: float = Field(0, description="Charge energy")

    @validator("seconds_recharge", always=True)
    def calculate_seconds_recharge(cls, value, values):
        sync_at = values.get("sync_at")
        if sync_at:
            seconds = (int(datetime.utcnow().timestamp()) - int(sync_at.timestamp()))
            return seconds if seconds < 10800 else 10800
        return 0


class STopUsers(BaseModel):
    telegram_id: int = Field(..., description="Telegram ID")
    username: Optional[str] = Field(None, description="Telegram username")
    balance: int = Field(0, description="Balance in LUNATERRA (minimal units)")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "telegram_id": 1234567890,
                "username": "johndoe",
                "balance": 0,
            }
        }


class SReferredUsers(STopUsers):
    id: int = Field(..., description="Unique user ID")
    invitation_bonus: int = Field(0, description="Invitation bonus in LUNATERRA (minimal units)")
    registration_date: datetime = Field(..., description="Registration date")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1234567890,
                "telegram_id": 1234567890,
                "username": "johndoe",
                "firstname": "John",
                "lastname": "Doe",
                "invitation_bonus": 0,
                "registration_date": "2022-01-01T00:00:00",
            }
        }

class SUserBase(BaseModel):
    telegram_id: int = Field(..., description="Telegram ID")
    username: Optional[str] = Field(None, description="Telegram username")
    balance: int = Field(0, description="Balance in LUNATERRA (minimal units)")
    wallet: Optional[str] = Field(None, description="Connected wallet")
    referral_code: Optional[str] = Field(None, description="Referral code")
    referred_by: Optional[int] = Field(None, description="ID of the referrer")
    is_subscribed: bool = Field(False, description="Subscription to the channel")
    firstname: Optional[str] = Field(None, description="First name")
    lastname: Optional[str] = Field(None, description="Last name")
    lang_code: Optional[str] = Field(None, description="Language code")
    is_premium: Optional[bool] = Field(None, description="Premium user status")
    sync_at: Optional[datetime] = Field(None, description="Last synchronization date")


class SUserCreate(SUserBase):
    pass


class SUserUpdate(SUserBase):
    telegram_id: Optional[int] = Field(None, description="Telegram ID")
    balance: Optional[int] = Field(None, description="Balance in LUNATERRA (minimal units)")
    is_subscribed: Optional[bool] = Field(None, description="Subscription to the channel")

class SUserWithoutReferral(SUserBase):
    id: int = Field(..., description="Unique user ID")
    registration_date: datetime = Field(..., description="Registration date")
    created_at: datetime = Field(..., description="Timestamp of the user creation")
    updated_at: datetime = Field(..., description="Timestamp of the user update")
    deleted_at: Optional[datetime] = Field(None, description="Timestamp of the user deletion")
    referral_link: Optional[str] = Field(
        None, description="Telegram referral link"
    )

    @validator("referral_link", always=True, pre=True)
    def generate_referral_link(cls, _, values):
        referral_code = values.get("referral_code")
        if referral_code:
            return f"https://t.me/lunaterra_bot?start=ref={referral_code}"
        return None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "telegram_id": 1234567890,
                "username": "johndoe",
                "balance": 0,
                "wallet": "0x1234567890abcdef",
                "is_subscribed": False,
                "id": 1234567890,
                "registration_date": "2022-01-01T00:00:00",
                "referral_link": "https://t.me/lunaterra_bot?start=ref=abcdef",
            }
        }

class SUserRead(SUserBase):
    id: int = Field(..., description="Unique user ID")
    registration_date: datetime = Field(..., description="Registration date")
    referred_users: List["SUserWithoutReferral"] = Field([], description="List of referred users")
    created_at: datetime = Field(..., description="Timestamp of the user creation")
    updated_at: datetime = Field(..., description="Timestamp of the user update")
    deleted_at: Optional[datetime] = Field(None, description="Timestamp of the user deletion")
    referral_link: Optional[str] = Field(
        None, description="Telegram referral link"
    )

    @validator("referral_link", always=True, pre=True)
    def generate_referral_link(cls, _, values):
        referral_code = values.get("referral_code")
        if referral_code:
            return f"https://t.me/lunaterra_bot?start=ref={referral_code}"
        return None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "telegram_id": 1234567890,
                "username": "johndoe",
                "balance": 0,
                "wallet": "0x1234567890abcdef",
                "referral_code": "abcdef",
                "referral_link": "https://t.me/lunaterra_bot?start=ref=abcdef",
                "referred_by": 1234567890,
                "is_subscribed": False,
                "id": 1234567890,
                "registration_date": "2022-01-01T00:00:00",
                "referred_users": [],
            }
        }


class SReferralUser(SUserBase):
    id: int = Field(..., description="Unique user ID")
    invitation_bonus: int = Field(0, description="Invitation bonus in LUNATERRA (minimal units)")
    registration_date: datetime = Field(..., description="Registration date")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1234567890,
                "telegram_id": 1234567890,
                "username": "johndoe",
                "firstname": "John",
                "lastname": "Doe",
                "invitation_bonus": 0,
                "registration_date": "2022-01-01T00:00:00",
                "referred_by": 1234567890,
                "lang_code": "en",
                "is_premium": False,
                "is_subscribed": False,
            }
        }
