import json

from redis.asyncio import Redis

from src.api.deps import get_redis_client
from src.core.config import settings
from src.utils.currency_LUNA_to_USDT import get_luna_price_binance
import math

async def calculate_energy():
    redis: Redis = await get_redis_client()

    current_price = get_luna_price_binance()
    if current_price is None:
        raise ValueError("Failed to fetch LUNA price")

    # daily_limit = settings.DAILY_LIMIT_USD * current_price
    daily_limit = math.floor(settings.DAILY_LIMIT_USD * current_price)

    # print('daily_limit:', daily_limit)

    daily_limit = daily_limit * 10000 # 10^4
    charge_per_second = daily_limit / (24 * 60 * 60)
    max_energy_per_part = charge_per_second * settings.SECONDS_MAX_RECHARGE
    discharge_per_click = max_energy_per_part / settings.MAX_CLICKS_PER_PARTITION

    # print('max_energy_per_part:', max_energy_per_part)
    # print(f'discharge_per_click: {discharge_per_click}= {max_energy_per_part} / {settings.MAX_CLICKS_PER_PARTITION}')

    data = {
        "current_price": current_price,
        "daily_limit": daily_limit,
        "charge_per_second": math.floor(round(charge_per_second, 3) * 20) / 20,
        "max_energy_per_part": max_energy_per_part,
        "discharge_per_click": discharge_per_click
    }

    redis_data = await redis.set(
        "energy:calc",
        json.dumps(data),
        ex=int (3 * 60 * 60)  # 3 hours
    )

    if redis_data is None:
        raise ValueError("Failed to set energy data to redis, energy:calc")
    print('redis_data', redis_data)

    return data

if __name__ == "__main__":
    energy_data = calculate_energy()
    for key, value in energy_data.items():
        print(f"{key}: {value}")