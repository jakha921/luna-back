import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_redis_client
from src.db.session import get_session
from src.repositories.user import UserRepository
from src.schemas.common import IGetResponseBase
from src.schemas.user import SGetSyncBalance, SSyncBalance
from src.utils.energy_calc import calculate_energy

router = APIRouter()


def get_user_repository(session: AsyncSession = Depends(get_session)) -> UserRepository:
    """Dependency to get the user repository."""
    return UserRepository(db=session)


async def get_cached_energy(redis: Redis) -> dict:
    """Fetch energy from Redis cache or calculate if not present."""
    cached_energy = await redis.get("energy:calc")
    return json.loads(cached_energy) if cached_energy else await calculate_energy()


@router.post(
    "/{telegram_id}",
    response_description="Sync energy calculation",
    response_model=IGetResponseBase[SGetSyncBalance],
    status_code=status.HTTP_201_CREATED,
    summary="Sync energy calculation"
)
async def sync_energy(
        telegram_id: int,
        obj_in: SSyncBalance,
        redis: Redis = Depends(get_redis_client)
) -> IGetResponseBase[SGetSyncBalance]:
    """Stores user energy balance in Redis cache."""
    cache_key = f"user:energy:{telegram_id}"

    data = {
        "balance": obj_in.balance,
        "value": obj_in.value,
        "sync_at": datetime.utcnow().isoformat()
    }

    try:
        await redis.set(cache_key, json.dumps(data), ex=5 * 24 * 60 * 60)  # 5 days
    except ConnectionError as e:
        raise HTTPException(status_code=500, detail=f"Redis connection error: {str(e)}")

    return IGetResponseBase(data=SGetSyncBalance(**data))


@router.get(
    "/{telegram_id}",
    response_description="Get sync energy calculation",
    response_model=IGetResponseBase[SGetSyncBalance],
    summary="Get sync energy calculation"
)
async def get_sync_energy(
        telegram_id: int,
        redis: Redis = Depends(get_redis_client)
) -> IGetResponseBase[SGetSyncBalance]:
    """Fetches user energy balance from Redis and calculates additional energy if needed."""
    cache_key = f"user:energy:{telegram_id}"
    cached_data = await redis.get(cache_key)
    energy = await get_cached_energy(redis)

    # Fetch energy values from Redis or calculate them
    charge_rate = energy.get("charge_per_second", 1)
    max_energy = energy.get("max_energy_per_part")

    if cached_data:
        data = json.loads(cached_data)
        res = SGetSyncBalance(**data)

        # Update value with recalculated energy
        res.value = min(res.value + charge_rate * res.seconds_recharge, max_energy)

        res.charge_per_second = charge_rate
        # res.charge_energy = max_energy

        return IGetResponseBase(data=res)

    # Return default if no data is found
    return IGetResponseBase(
        data=SGetSyncBalance(
            balance=0,
            value=max_energy,
            sync_at=datetime.utcnow(),
            seconds_recharge=0,
            charge_per_second=charge_rate,
        )
    )
