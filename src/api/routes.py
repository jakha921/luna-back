from fastapi import APIRouter, status
from fastapi.responses import PlainTextResponse, Response

from src.api.v1 import user, wallet, sync_energy, sync_management

from src.utils import sentry_app

home_router = APIRouter()


@home_router.get("/", response_description="Homepage", include_in_schema=False)
async def home() -> Response:
    return PlainTextResponse("LunaTerra API", status_code=status.HTTP_200_OK)


api_router = APIRouter()
api_router.include_router(user.router, tags=["User"], prefix="/user")
api_router.include_router(sync_energy.router, tags=["Sync Energy"], prefix="/user/sync_energy")
api_router.include_router(wallet.router, tags=["Wallet"], prefix="/wallet")
api_router.include_router(sync_management.router, tags=["Sync Management"], prefix="/sync-management")
api_router.include_router(sentry_app.router, tags=["Sentry"], prefix="/sentry")
