from fastapi import APIRouter
from fastapi_cache.decorator import cache

from src.schemas.common import IGetResponseBase
from src.utils.currency_LUNA_to_USDT import get_luna_price_binance
from src.utils.ton_api import withdraw

router = APIRouter()


@router.post("/withdraw")
async def wallet_withdraw(amount: float, telegram_id: int):
    return withdraw(amount, telegram_id)


@router.get("/currency")
@cache(
    expire=60 * 60
)  # cache for 1 hours
async def get_currency():
    return IGetResponseBase(data=get_luna_price_binance())