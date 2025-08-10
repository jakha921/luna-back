import logging
from datetime import datetime
from typing import List
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import lazyload
from sqlmodel import select

from src.core.exceptions import DuplicateObjectException, DatabaseException, ObjectNotFoundException
from src.models.user import User
from src.repositories.sqlalchemy import BaseSQLAlchemyRepository, ModelType
from src.schemas.user import SUserCreate, SUserUpdate
from src.utils.currency_LUNA_to_USDT import get_luna_price_binance
from src.utils.logger import get_logger

logger = get_logger(__name__)


class UserRepository(BaseSQLAlchemyRepository[User, SUserCreate, SUserUpdate]):
    _model = User
    _join_models = ["referred_users"]

    # def __init__(self, db: AsyncSession) -> None:
    #     super().__init__(
    #         db=db,
    #         join_models=["referred_users"],
    #     )

    async def create(self, obj_in: SUserCreate) -> User:
        """
        Create a new user in the database with a default referral code if not provided.
        """
        data = obj_in.dict(exclude_unset=True)
        if "referral_code" not in data or data["referral_code"] is None:
            generated_code = str(uuid4())[:8]  # Generate a new referral code

            # check if the generated referral code already exists
            while await self.f(referral_code=generated_code):
                generated_code = str(uuid4())[:8]

            data["referral_code"] = generated_code

        logger.debug(f"User creation data: {data}")
        if "referred_by" in data and data["referred_by"]:
            logger.debug(f"Processing referral for user: {data['referred_by']}")

            luna_price = get_luna_price_binance()
            if luna_price is None or luna_price <= 0:
                raise ValueError("LUNA price must be positive and non-zero")

            # calculate the bonus: $50 worth of LUNA at current price
            data["invitation_bonus"] = int((50 / luna_price) * 1000000)
            # add $50 worth of LUNA to inviter user balance
            inviter_user = await self.get(id=data["referred_by"])
            inviter_user.balance += data["invitation_bonus"]

        # add sync date
        if "sync_at" not in data or data["sync_at"] is None:
            data["sync_at"] = datetime.utcnow()

        db_obj = self._model(**data)
        self.db.add(db_obj)
        try:
            await self.db.commit()
            await self.db.refresh(db_obj)
            return db_obj
        except IntegrityError as exc:
            await self.db.rollback()
            logger.error(f"IntegrityError during user creation: {exc}")
            raise DuplicateObjectException("User with the given identifier already exists.") from exc
        except SQLAlchemyError as exc:
            await self.db.rollback()
            logger.error(f"SQLAlchemyError during user creation: {exc}")
            raise DatabaseException("An error occurred while creating the user.") from exc

    async def all(
            self,
            page: int = 1,
            limit: int = 20,
            sort_field: str = "created_at",
            sort_order: str = "desc",
    ) -> List[ModelType]:
        """
        Retrieve all objects from the database with optional pagination and sorting.

        Args:
            page (int): Page number for pagination. Defaults to 1.
            limit (int): Maximum number of records to return. Defaults to 100.
            sort_field (str): Field to sort by. Defaults to "created_at".
            sort_order (str): Sort order ("asc" or "desc"). Defaults to "desc".

        Returns:
            List[ModelType]: List of retrieved objects.
        """
        logger.info(f"Fetching all {self._model.__name__} objects.")

        if not hasattr(self._model, sort_field):
            logger.error(f"Invalid sort_field '{sort_field}' for {self._model.__name__}.")
            raise ValueError(f"Invalid sort_field '{sort_field}' for {self._model.__name__}.")

        order_column = getattr(self._model, sort_field)
        order_func = getattr(order_column, sort_order, None)
        if not order_func:
            logger.error(f"Invalid sort_order '{sort_order}'.")
            raise ValueError(f"Invalid sort_order '{sort_order}'.")

        query = (
            select(self._model).
            options(lazyload(User.referred_users)).
            order_by(order_func()).
            offset((limit * (page - 1))).
            limit(limit)
        )

        try:
            result = await self.db.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as exc:
            logger.error(f"Error fetching {self._model.__name__} objects: {exc}")
            raise DatabaseException(f"An error occurred while fetching objects: {exc}") from exc

    async def get_place_on_top(self, telegram_id: int) -> int:
        """
        Get the current user's place on the leaderboard by balance.

        Args:
            telegram_id (int): The Telegram ID of the user.

        Returns:
            int: The user's rank based on balance.
        """
        # Create a subquery to rank users by balance
        subquery = (
            select(
                self._model.telegram_id,
                func.rank().over(order_by=self._model.balance.desc()).label("rank")
            )
            .subquery()
        )

        # Query the rank for the given user
        query = select(subquery.c.rank).where(subquery.c.telegram_id == telegram_id)

        try:
            result = await self.db.execute(query)
            rank = result.scalar_one_or_none()
            if rank is None:
                raise ObjectNotFoundException(f"User with telegram_id {telegram_id} not found.")
            return rank
        except SQLAlchemyError as exc:
            logger.error(f"Error fetching user rank: {exc}")
            raise DatabaseException("An error occurred while fetching the user's rank.") from exc

    async def get_referred_users(self, telegram_id: int) -> List[ModelType]:
        """
        Get a list of users referred by the given user.

        Args:
            telegram_id (int): The Telegram ID of the user.

        Returns:
            List[ModelType]: List of referred users.
        """
        logger.info(f"Fetching referred users for user with telegram_id {telegram_id}.")

        query = (
            select(self._model).
            where(
                self._model.referred_by == (
                    select(User.id).where(User.telegram_id == telegram_id)
                )
            ).options(lazyload(User.referred_users))
        )

        try:
            result = await self.db.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as exc:
            logger.error(f"Error fetching referred users: {exc}")
            raise DatabaseException("An error occurred while fetching referred users.") from exc

    async def get_total_user_counter(self) -> int:
        """
        Get the total number of users in the database.

        Returns:
            int: The total number of users.
        """
        logger.info("Fetching total user count.")
        try:
            query = select(func.count(self._model.id))
            result = await self.db.execute(query)
            return result.scalar_one_or_none() or 0
        except SQLAlchemyError as exc:
            logger.error(f"Error fetching total user count: {exc}")
            raise DatabaseException("An error occurred while fetching the total user count.") from exc

    async def sync_balances_from_redis(self, redis_data: dict) -> dict:
        """
        Синхронизирует балансы пользователей из Redis в базу данных.
        
        Args:
            redis_data (dict): Словарь {telegram_id: balance} из Redis
            
        Returns:
            dict: Статистика синхронизации
        """
        logger.info(f"Starting balance synchronization for {len(redis_data)} users.")
        
        updated_count = 0
        not_found_count = 0
        error_count = 0
        sync_time = datetime.utcnow()
        
        try:
            for telegram_id_str, balance_str in redis_data.items():
                try:
                    telegram_id = int(telegram_id_str)
                    balance = int(float(balance_str))  # Convert to int for database
                    
                    # Найти пользователя по telegram_id
                    user = await self.get(telegram_id=telegram_id)
                    if user:
                        # Обновить баланс и время синхронизации
                        user.balance = balance
                        user.sync_at = sync_time
                        self.db.add(user)
                        updated_count += 1
                        logger.debug(f"Updated balance for user {telegram_id}: {balance}")
                    else:
                        not_found_count += 1
                        logger.warning(f"User with telegram_id {telegram_id} not found in database")
                        
                except (ValueError, TypeError) as e:
                    error_count += 1
                    logger.error(f"Error processing telegram_id {telegram_id_str}, balance {balance_str}: {e}")
                except Exception as e:
                    error_count += 1
                    logger.error(f"Unexpected error processing user {telegram_id_str}: {e}")
                    
            # Сохранить все изменения
            await self.db.commit()
            
            result = {
                "updated": updated_count,
                "not_found": not_found_count,
                "errors": error_count,
                "total_processed": len(redis_data),
                "sync_time": sync_time.isoformat()
            }
            
            logger.info(f"Balance synchronization completed: {result}")
            return result
            
        except SQLAlchemyError as exc:
            await self.db.rollback()
            logger.error(f"Database error during balance synchronization: {exc}")
            raise DatabaseException(f"Database error during synchronization: {exc}") from exc
        except Exception as exc:
            await self.db.rollback()
            logger.error(f"Unexpected error during balance synchronization: {exc}")
            raise DatabaseException(f"Unexpected error during synchronization: {exc}") from exc
