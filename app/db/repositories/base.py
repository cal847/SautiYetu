"""
app/db/repositories/base.py
---------------------------
Generic async repository providing common CRUD operations.
All domain repositories inherit from this class.
"""

from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Thin async CRUD base — subclass and set `model`."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_by_id(self, record_id: Any) -> ModelT | None:
        """Return a single record by primary key, or None."""
        return await self.session.get(self.model, record_id)

    async def list(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        order_by: Any = None,
    ) -> list[ModelT]:
        """Return a paginated list of records."""
        stmt = select(self.model)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        """Return total row count for the model's table."""
        from sqlalchemy import func, select

        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create(self, instance: ModelT) -> ModelT:
        """Persist a new instance and flush to get DB-generated values."""
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, instance: ModelT, **kwargs: Any) -> ModelT:
        """Apply keyword updates to an existing instance and flush."""
        for field, value in kwargs.items():
            setattr(instance, field, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        """Delete an instance and flush."""
        await self.session.delete(instance)
        await self.session.flush()