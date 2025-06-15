import sentry_sdk
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from starlette.responses import JSONResponse

from src.api import routes
from src.api.deps import get_redis_client
from src.core.config import settings
from src.utils.logger import init_logger, get_logger

# Инициализация loguru логирования
init_logger()
logger = get_logger(__name__)

# Set up sentry - временно отключено до решения проблем совместимости с loguru
# try:
#     sentry_sdk.init(
#         dsn="https://9d2f9bd9dc47aac4522f76468df274a5@o4508393506603008.ingest.de.sentry.io/4508402366939216",
#         # Отключаем автоматические интеграции чтобы исключить loguru
#         auto_enabling_integrations=False,
#         # Включаем только нужные интеграции без loguru
#         integrations=[
#             sentry_sdk.integrations.fastapi.FastApiIntegration(),
#             sentry_sdk.integrations.asyncio.AsyncioIntegration(),
#             sentry_sdk.integrations.stdlib.StdlibIntegration(),
#             # LoguruIntegration исключена
#         ],
#     )
#     logger.success("Sentry initialized successfully without loguru integration")
# except Exception as e:
#     logger.warning(f"Failed to initialize Sentry: {e}")
#     # Продолжаем работу без Sentry

logger.info("Application starting without Sentry (temporarily disabled for loguru compatibility)")

app = FastAPI(
    title="Luna Terra API",
    description="API for Luna Terra project",
    version=settings.VERSION,
    openapi_url=f"/{settings.API_PREFIX}/openapi.json",
    # openapi_tags=tags_metadata,
)


async def on_startup() -> None:
    # await add_postgresql_extension()
    redis_client = await get_redis_client()
    FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")
    logger.info("FastAPI app running...")


list_of_domens = [
    # "http://localhost",
    # "http://localhost:3000",
    # "http://localhost:8000",

    # "https://luna-api.ruzibaev.uz",
    # "https://luna-front.ruzibaev.uz",

    # "https://lunaterra.vercel.app/",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=list_of_domens,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_event_handler("startup", on_startup)

app.include_router(routes.home_router)
app.include_router(routes.api_router, prefix=f"/{settings.API_PREFIX}")


# Error handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail
        }
    )


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
