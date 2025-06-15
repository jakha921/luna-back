import logging
from typing import Any, Generic, List, Optional, Type, TypeVar

from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import SQLModel, select

from src.core.exceptions import (
    DatabaseException,
    ObjectNotFoundException,
    DuplicateObjectException
)
from src.interfaces.repository import IRepository

# Define type variables for the model, create schema, and update schema
ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=SQLModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=SQLModel)

logger = logging.getLogger(__name__)


class BaseSQLAlchemyRepository(
    IRepository, Generic[ModelType, CreateSchemaType, UpdateSchemaType]
):
    """
    Base repository class for SQLAlchemy operations.

    Attributes:
        _model (Type[ModelType]): The model class associated with the repository.
        db (AsyncSession): The asynchronous database session.
    """

    _model: Type[ModelType]
    _join_models: List[str]

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize the repository with a database session.

        Args:
            db (AsyncSession): The asynchronous database session.
            join_models (List[str]): List of related models to join when fetching objects.
        """
        self.db = db
        # self.join_models = join_models

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        """
        Create a new object in the database.

        Args:
            obj_in (CreateSchemaType): The input schema for creating the object.

        Returns:
            ModelType: The created database object.
        """
        logger.info(f"Creating a new {self._model.__name__} object.")

        db_obj = self._model.from_orm(obj_in)
        self.db.add(db_obj)
        try:
            await self.db.commit()
            await self.db.refresh(db_obj)
            logger.info(f"{self._model.__name__} object created with ID {db_obj.id}.")
            return db_obj

        except IntegrityError as exc:
            await self.db.rollback()
            logger.error(f"Integrity error creating {self._model.__name__}: {exc}")
            raise DuplicateObjectException(f"{self._model.__name__} already exists.") from exc
        except SQLAlchemyError as exc:
            await self.db.rollback()
            logger.error(f"Error creating {self._model.__name__}: {exc}")
            raise DatabaseException("An error occurred while creating the object.") from exc

    async def get(self, **kwargs: Any) -> Optional[ModelType]:
        """
        Retrieve an object from the database based on provided filters.

        Args:
            **kwargs: Filter criteria for querying the object.

        Returns:
            Optional[ModelType]: The retrieved object or None if not found.
        """
        logger.info(f"Fetching {self._model.__name__} object with filters {kwargs}.")
        query = select(self._model).filter_by(**kwargs)

        # Apply eager loading for joined models if needed
        for join_model in self._join_models:
            query = query.options(selectinload(getattr(self._model, join_model)))

        try:
            result = await self.db.execute(query)
            # Use unique() to handle joined loads against collections
            obj = result.unique().scalar_one_or_none()
            if obj is None:
                logger.warning(f"{self._model.__name__} not found with filters {kwargs}.")
                raise ObjectNotFoundException(f"{self._model.__name__} not found.")
            return obj
        except SQLAlchemyError as exc:
            logger.error(f"Error fetching {self._model.__name__}: {exc}")
            raise DatabaseException("An error occurred while fetching the object.") from exc

    async def update(
            self, obj_current: ModelType, obj_in: UpdateSchemaType
    ) -> ModelType:
        """
        Update an existing object in the database.

        Args:
            obj_current (ModelType): The current database object.
            obj_in (UpdateSchemaType): The input schema with updated data.

        Returns:
            ModelType: The updated database object.
        """
        logger.info(f"Updating {self._model.__name__} object with ID {obj_current.id}.")
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(obj_current, field, value)
        try:
            await self.db.commit()
            await self.db.refresh(obj_current)
            logger.info(f"{self._model.__name__} object with ID {obj_current.id} updated.")
            return obj_current
        except SQLAlchemyError as exc:
            await self.db.rollback()  # <-- rollback transaction if error occurs
            logger.error(f"Error updating {self._model.__name__}: {exc}")
            raise DatabaseException("An error occurred while updating the object.") from exc

    async def delete(self, **kwargs: Any) -> None:
        """
        Delete an object from the database based on provided filters.

        Args:
            **kwargs: Filter criteria for querying the object to delete.
        """
        logger.info(f"Deleting {self._model.__name__} object with filters {kwargs}.")
        obj = await self.get(**kwargs)
        try:
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"{self._model.__name__} object deleted.")
        except SQLAlchemyError as exc:
            await self.db.rollback()
            logger.error(f"Error deleting {self._model.__name__}: {exc}")
            raise DatabaseException("An error occurred while deleting the object.") from exc

    async def all(
            self,
            page: int = 1,
            limit: int = 100,
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
            order_by(order_func()).
            offset((page - 1) * limit).
            limit(limit)
        )
        try:
            result = await self.db.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as exc:
            logger.error(f"Error fetching {self._model.__name__} objects: {exc}")
            raise DatabaseException(f"An error occurred while fetching objects: {exc}") from exc

    async def f(self, **kwargs: Any) -> List[ModelType]:
        """
        Retrieve objects from the database based on provided filters.

        Args:
            **kwargs: Filter criteria for querying the objects.

        Returns:
            List[ModelType]: List of retrieved objects.
        """
        logger.info(f"Fetching {self._model.__name__} objects by {kwargs}.")

        query = select(self._model).filter_by(**kwargs)
        try:
            result = await self.db.execute(query)
            scalars = result.scalars().all()
            return scalars
        except SQLAlchemyError as exc:
            logger.error(f"Error fetching {self._model.__name__} objects: {exc}")
            raise DatabaseException("An error occurred while fetching objects.")

    async def get_or_create(
            self, obj_in: CreateSchemaType, **kwargs: Any
    ) -> ModelType:
        """
        Retrieve an object from the database or create it if it does not exist.

        Args:
            obj_in (CreateSchemaType): The input schema for creating the object.
            **kwargs: Filter criteria for querying the object.

        Returns:
            ModelType: The retrieved or created database object.
        """
        logger.info(f"Getting or creating {self._model.__name__} with {kwargs}.")
        instance = await self.get(**kwargs)
        if instance:
            logger.info(f"Found existing {self._model.__name__} object.")
            return instance
        else:
            logger.info(
                f"No existing {self._model.__name__} found. Creating a new one."
            )
            return await self.create(obj_in)

    async def bulk_create(self, objs_in: List[CreateSchemaType]) -> List[ModelType]:
        """
        Bulk create multiple objects in the database.

        Args:
            objs_in (List[CreateSchemaType]): A list of input schemas for creating the objects.

        Returns:
            List[ModelType]: The list of created database objects.
        """
        logger.info(f"Bulk creating {len(objs_in)} {self._model.__name__} objects.")

        # Convert input schemas to dictionaries
        objs_data = [obj_in.dict(exclude_unset=True) for obj_in in objs_in]

        # Create an insert statement with returning clause to get inserted records
        # stmt = insert(self._model).values(objs_data).returning(self._model)
        stmt = self._model.__table__.insert().values(objs_data).returning(self._model)

        try:
            # Execute the statement
            result = await self.db.execute(stmt)
            await self.db.commit()

            # Fetch all inserted records
            inserted_records = result.fetchall()

            # Convert inserted records to model instances
            inserted_objs = [self._model(**dict(record)) for record in inserted_records]

            logger.info(
                f"Bulk created {len(inserted_objs)} {self._model.__name__} objects."
            )
            return inserted_objs
        except SQLAlchemyError as exc:
            await self.db.rollback()
            logger.error(f"Error bulk creating {self._model.__name__} objects: {exc}")
            raise DatabaseException("An error occurred while bulk creating objects.") from exc
