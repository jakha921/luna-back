from datetime import datetime

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class BaseModel(SQLModel):
    id: int = Field(
        default=None,
        primary_key=True,
        index=True
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=sa.DateTime(timezone=True),
        sa_column_kwargs={"onupdate": sa.func.now(), "server_default": sa.func.now()},
    )
    created_at: datetime | None = Field(
        default=None,
        sa_type=sa.DateTime(timezone=True),
        sa_column_kwargs={"server_default": sa.func.now()},
        nullable=False,
    )
    deleted_at: datetime | None = Field(
        default=None,
        sa_type=sa.DateTime(timezone=True),
        nullable=True,
    )

    class Config:
        from_attributes = True
        # orm_mode = True
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}