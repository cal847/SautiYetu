"""
app/db/repositories/bill_repository.py
---------------------------------------
Repository for the `bills` table.

Responsibilities
----------------
- CRUD + upsert for Bill records
- Filtered, paginated listing (status, category)
- Deduplication check by source_url / content_hash
- Eager-load helpers for API responses
"""

from enum import Enum

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models.bill import Bill
from app.db.repositories.base import BaseRepository


class UpsertResult(str, Enum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    SKIPPED = "SKIPPED"


class BillRepository(BaseRepository[Bill]):
    model = Bill

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def get_by_id_with_relations(self, bill_id: str) -> Bill | None:
        """Return a Bill with content + ai_insight eagerly loaded."""
        stmt = (
            select(Bill)
            .where(Bill.id == bill_id)
            .options(
                selectinload(Bill.content),
                selectinload(Bill.ai_insight),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_source_url(self, source_url: str) -> Bill | None:
        """Look up a bill by its canonical parliament URL."""
        stmt = select(Bill).where(Bill.source_url == source_url)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_filtered(
        self,
        *,
        status: str | None = None,
        category: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Bill]:
        """
        Return a paginated, filtered bill list — newest first.
        Optionally eager-loads ai_insight for summary excerpts.
        """
        stmt = (
            select(Bill)
            .options(selectinload(Bill.ai_insight))
            .order_by(Bill.created_at.desc())
        )
        if status:
            stmt = stmt.where(Bill.status == status)
        if category:
            stmt = stmt.where(Bill.category == category)

        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_filtered(
        self,
        *,
        status: str | None = None,
        category: str | None = None,
    ) -> int:
        """Return total count matching the same filters (for pagination metadata)."""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(Bill)
        if status:
            stmt = stmt.where(Bill.status == status)
        if category:
            stmt = stmt.where(Bill.category == category)

        result = await self.session.execute(stmt)
        return result.scalar_one()

    # ------------------------------------------------------------------
    # Upsert / deduplication
    # ------------------------------------------------------------------

    async def upsert(self, bill_data: dict) -> tuple[Bill, UpsertResult]:
        """
        Insert or update a bill based on `source_url`.

        - If no record exists               → INSERT  → CREATED
        - If record exists, hash changed    → UPDATE  → UPDATED
        - If record exists, hash unchanged  → no-op   → SKIPPED

        `bill_data` must include at minimum:
            id, title, status, source_url, content_hash
        """
        existing = await self.get_by_source_url(bill_data["source_url"])

        if existing is None:
            bill = Bill(**bill_data)
            await self.create(bill)
            return bill, UpsertResult.CREATED

        incoming_hash = bill_data.get("content_hash")
        if existing.content_hash and existing.content_hash == incoming_hash:
            return existing, UpsertResult.SKIPPED

        updatable_fields = {
            k: v
            for k, v in bill_data.items()
            if k not in {"id", "source_url", "created_at"}
        }
        updated = await self.update(existing, **updatable_fields)
        return updated, UpsertResult.UPDATED
