from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session
from src.repositories.user import UserRepository
from src.schemas.common import IGetResponseBase
from src.schemas.user import SUserRead, SUserCreate

router = APIRouter()


@router.get(
    "/",
    response_description="Get all users",
    response_model=IGetResponseBase[List[SUserRead]],
)
async def get_integrators(
        session: AsyncSession = Depends(get_session),
) -> IGetResponseBase[List[SUserRead]]:
    integrator_repo = UserRepository(db=session)
    integrators = await integrator_repo.all()

    return integrators
    # return IGetResponseBase[List[SUserRead]](data=[integrator.dict() for integrator in integrators])

@router.post(
    "/",
    response_description="Create new integrator",
    response_model=IGetResponseBase[SUserCreate],
)
async def create_integrator(
    integrator: SUserCreate,
    session: AsyncSession = Depends(get_session),
) -> IGetResponseBase[SUserCreate]:
    integrator_repo = UserRepository(db=session)
    integrator_resp = await integrator_repo.get_or_create(
        integrator, email=integrator.email
    )

    return IGetResponseBase[SUserCreate](data=integrator_resp.dict())

# create user
# @router.post(
#     "/",
#     response_description="Create new user",
#     response_model=IGetResponseBase[SUserCreate],
# )
# async def create_user(
#         user: SUserCreate,
#         session: AsyncSession = Depends(get_session),
# ) -> IGetResponseBase[SUserCreate]:
#     user_repo = UserRepository(db=session)
#     print('user:', user)
#     user_resp = await user_repo.get_or_create(user, email=user.email)
#     print('user_resp:', user_resp)
#
#     return IGetResponseBase[SUserCreate](data=user_resp)
