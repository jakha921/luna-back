import asyncio
from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from redis.asyncio.client import Redis
from redis.exceptions import ConnectionError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.api.deps import get_redis_client
from src.db.session import get_session
from src.models.user import User
from src.repositories.user import UserRepository
from src.schemas.common import IGetResponseBase
from src.schemas.user import SUserRead, SUserCreate, SUserUpdate, SUserWithoutReferral, STopUsers, SReferredUsers
from src.utils.cache import user_cache_key_builder
from src.utils.energy_calc import calculate_energy
from src.utils.logger import get_logger
from src.utils.redis_sync import get_all_telegram_balances

logger = get_logger(__name__)

router = APIRouter()


def get_user_repository(
        session: AsyncSession = Depends(get_session),
) -> UserRepository:
    return UserRepository(db=session)


@router.get(
    "",
    response_description="Get all users",
    response_model=IGetResponseBase[List[SUserRead]],
    summary="Get all users"
)
async def get_users(
        user_repo: UserRepository = Depends(get_user_repository),
) -> IGetResponseBase[List[SUserWithoutReferral]]:
    users = await user_repo.all()
    users_read = [SUserWithoutReferral.from_orm(user) for user in users]
    return IGetResponseBase(data=users_read)


@router.get(
    "/referral-code/{referral_code}",
    response_description="Get user by referral_code",
    response_model=IGetResponseBase[int],
    summary="Get user by referral_code"
)
async def get_user_by_referral_code(
        referral_code: str,
        user_repo: UserRepository = Depends(get_user_repository),
) -> IGetResponseBase[int]:
    user = await user_repo.get(referral_code=referral_code)
    return IGetResponseBase(data=user.id)


# CRUD
# Create, Read, Update, Delete
@router.post(
    "",
    response_description="Create new user",
    response_model=IGetResponseBase[SUserRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create new user"
)
async def create_user(
        obj_in: SUserCreate,
        user_repo: UserRepository = Depends(get_user_repository),
) -> IGetResponseBase[SUserWithoutReferral]:
    logger.info(f"Creating user: {obj_in.dict()}")
    user = await user_repo.create(obj_in=obj_in)
    user_read = SUserWithoutReferral.from_orm(user)
    return IGetResponseBase(data=user_read)


@router.get(
    "/full_user/{telegram_id}",
    response_description="Get user by telegram_id",
    # response_model=IGetResponseBase[SUserRead],
    summary="Get user by telegram_id"
)
@cache(
    expire=30,
    key_builder=user_cache_key_builder
)  # cache for 1 hour
async def get_user(
        telegram_id: int,
        user_repo: UserRepository = Depends(get_user_repository),
):
    # Use caching (if enabled) to store and retrieve user data quickly
    user = await user_repo.get(telegram_id=telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Optimize queries using asyncio.gather for concurrent execution
        (
            top_users,
            user_place,
            referrals,
            total_users,
            energy
        ) = await asyncio.gather(
            user_repo.all(page=1, limit=20, sort_field="balance", sort_order="desc"),
            user_repo.get_place_on_top(telegram_id),
            user_repo.get_referred_users(telegram_id),
            user_repo.get_total_user_counter(),
            calculate_energy()  # Optimized async energy calculation
        )

        # Convert ORM objects to response schema
        top_users_read = [STopUsers.from_orm(u) for u in top_users]
        referred_users_read = [SReferredUsers.from_orm(u) for u in referrals]

        return IGetResponseBase(
            data={
                "user": SUserWithoutReferral.from_orm(user),
                "place_on_top": user_place,
                "top_users": top_users_read,
                "referred_users": referred_users_read,
                "total_users": total_users,
                "energy": energy
            }
        )

    except Exception as e:
        logger.error(f"Error fetching user data: {e}")
        raise HTTPException(status_code=404, detail="User data get error")


@router.patch(
    "/{telegram_id}",
    response_description="Update user by telegram_id",
    response_model=IGetResponseBase[SUserRead],
    summary="Update user by telegram_id"
)
async def update_user(
        telegram_id: int,
        obj_in: SUserUpdate,
        user_repo: UserRepository = Depends(get_user_repository),
) -> IGetResponseBase[SUserRead]:
    db_obj = await user_repo.get(telegram_id=telegram_id)
    user = await user_repo.update(obj_current=db_obj, obj_in=obj_in)
    user_read = SUserRead.from_orm(user)

    logger.debug("Starting cache invalidation")
    try:
        # Build cache key
        prefix = FastAPICache.get_prefix()
        cache_key = f"{prefix}:user_cache:{telegram_id}"

        # Attempt to delete cache key
        backend = FastAPICache.get_backend()
        logger.debug(f"Cache backend methods: {backend.__dir__()}")
        if hasattr(backend, "_client"):
            try:
                result = await backend._client.delete(cache_key)
                if result == 0:
                    logger.warning(f"Cache key {cache_key} does not exist.")
                else:
                    logger.info(f"Cache key {cache_key} deleted successfully.")
            except ConnectionError as e:
                logger.error(f"ConnectionError deleting cache key: {e}")
        else:
            logger.warning("Cache backend is not properly configured.")
    except Exception as e:
        logger.error(f"Error deleting cache key: {e}")

    return IGetResponseBase(data=user_read)


@router.delete(
    "/{telegram_id}",
    response_description="Delete user by telegram_id",
    response_model=IGetResponseBase[SUserRead],
    summary="Delete user by telegram_id"
)
async def delete_user(
        telegram_id: int,
        user_repo: UserRepository = Depends(get_user_repository),
) -> IGetResponseBase[SUserRead]:
    user = await user_repo.delete(telegram_id=telegram_id)
    return IGetResponseBase(data=None if user is None else SUserRead.from_orm(user))


@router.post(
    "/sync-from-redis",
    response_description="Sync user balances from Redis to database",
    response_model=IGetResponseBase[dict],
    summary="Sync balances from Redis",
    status_code=status.HTTP_200_OK
)
async def sync_balances_from_redis(
        user_repo: UserRepository = Depends(get_user_repository),
        redis_client: Redis = Depends(get_redis_client),
) -> IGetResponseBase[dict]:
    """
    Синхронизирует балансы пользователей из Redis в базу данных.
    Получает все ключи вида telegram_id из Redis и обновляет соответствующие балансы в БД.
    """
    try:
        # Получить все балансы пользователей из Redis
        redis_data = await get_all_telegram_balances(redis_client)
        
        if not redis_data:
            return IGetResponseBase(
                data={
                    "message": "No valid telegram_id balance data found in Redis",
                    "updated": 0,
                    "not_found": 0,
                    "errors": 0,
                    "total_processed": 0
                }
            )
        
        # Синхронизировать данные
        sync_result = await user_repo.sync_balances_from_redis(redis_data)
        sync_result["message"] = "Synchronization completed successfully"
        
        return IGetResponseBase(data=sync_result)
        
    except ConnectionError as e:
        logger.error(f"Redis connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Redis connection error. Unable to sync balances."
        )
    except Exception as e:
        logger.error(f"Error during synchronization: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during synchronization"
        )


@router.get(
    "/sync-stats",
    response_description="Get synchronization statistics",
    response_model=IGetResponseBase[dict],
    summary="Get sync statistics"
)
async def get_sync_statistics(
        user_repo: UserRepository = Depends(get_user_repository),
) -> IGetResponseBase[dict]:
    """
    Получает статистику синхронизации пользователей.
    Показывает сколько пользователей было синхронизировано и когда.
    """
    try:
        # Получить количество синхронизированных пользователей
        query = select(func.count(User.id), func.max(User.sync_at)).where(User.sync_at.is_not(None))
        result = await user_repo.db.execute(query)
        sync_count, last_sync = result.one()
        
        # Общее количество пользователей
        total_users = await user_repo.get_total_user_counter()
        
        return IGetResponseBase(
            data={
                "total_users": total_users,
                "synced_users": sync_count or 0,
                "unsynced_users": total_users - (sync_count or 0),
                "last_sync_time": last_sync.isoformat() if last_sync else None,
                "sync_coverage_percent": round((sync_count or 0) / max(total_users, 1) * 100, 2)
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting sync statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error retrieving synchronization statistics"
        )


# redis get data and update user