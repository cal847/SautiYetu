"""
app/db/repositories/insight_repository.py
------------------------------------------
Repository for the `ai_insights` table.

Responsibilities
----------------
- Create / update AI insight records
- Check if an insight already exists for a bill (pipeline dedup)
- Fetch insights for API responses
"""

from sqlalchemy import select

from app.db.models.ai_insight import AIInsight
from app.db.repositories.base import BaseRepository


class InsightRepository(BaseRepository[AIInsight]):
    model = AIInsight

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def get_by_bill_id(self, bill_id: str) -> AIInsight | None:
        """Return the AI insight for a given bill, or None."""
        stmt = select(AIInsight).where(AIInsight.bill_id == bill_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_for_bill(self, bill_id: str) -> bool:
        """
        Return True if an insight already exists for this bill.
        Used by the pipeline to skip re-analysis.
        """
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(AIInsight)
            .where(AIInsight.bill_id == bill_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def list_public_participation(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[AIInsight]:
        """Return insights where public_participation=True, newest first."""
        stmt = (
            select(AIInsight)
            .where(AIInsight.public_participation.is_(True))
            .order_by(AIInsight.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def upsert(self, insight_data: dict) -> AIInsight:
        """
        Insert a new insight or replace an existing one for the same bill_id.
        The pipeline always passes the full insight dict so a full replace
        is safe and correct.
        """
        existing = await self.get_by_bill_id(insight_data["bill_id"])

        if existing is None:
            insight = AIInsight(**insight_data)
            return await self.create(insight)

        updatable = {k: v for k, v in insight_data.items() if k != "bill_id"}
        return await self.update(existing, **updatable)
