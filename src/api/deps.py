from fastapi.security import HTTPBearer
from redis import asyncio as aioredis
from redis.asyncio import Redis

from src.core.config import settings


async def get_redis_client(
        # db_number: int = 1
) -> Redis:
    redis = await aioredis.from_url(
        f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
        password=settings.REDIS_PASSWORD,
        max_connections=10,
        encoding="utf8",
        decode_responses=True,
        db=0
    )
    return redis


bearer_security = HTTPBearer()
