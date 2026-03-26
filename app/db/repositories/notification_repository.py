"""
app/db/repositories/notification_repository.py
------------------------------------------------
Repository for the `notification_log` table.

Responsibilities
----------------
- Persist notification send records (success + failure)
- Deduplication check: has a successful SMS already been sent
  for a given bill + event_type combination?
- Provide the alerts feed for GET /alerts
"""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models.notification_log import NotificationLog
from app.db.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[NotificationLog]):
    model = NotificationLog

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    async def already_sent(self, bill_id: str, event_type: str) -> bool:
        """
        Return True if a *successful* SMS has already been sent
        for this bill_id + event_type pair.

        This is the primary deduplication gate in the notification service.
        """
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(NotificationLog)
            .where(
                NotificationLog.bill_id == bill_id,
                NotificationLog.event_type == event_type,
                NotificationLog.status == "success",
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def get_alerts_feed(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[NotificationLog]:
        """
        Return successful notification events, newest first.
        Eagerly loads the related bill for summary context in GET /alerts.
        """
        stmt = (
            select(NotificationLog)
            .where(NotificationLog.status == "success")
            .options(selectinload(NotificationLog.bill))
            .order_by(NotificationLog.sent_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_bill(self, bill_id: str) -> list[NotificationLog]:
        """Return all notification attempts for a specific bill."""
        stmt = (
            select(NotificationLog)
            .where(NotificationLog.bill_id == bill_id)
            .order_by(NotificationLog.sent_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def log_success(
        self,
        bill_id: str,
        event_type: str,
        recipient: str | None = None,
    ) -> NotificationLog:
        """Record a successful SMS send."""
        log = NotificationLog(
            bill_id=bill_id,
            type="SMS",
            event_type=event_type,
            recipient=recipient,
            status="success",
        )
        return await self.create(log)

    async def log_failure(
        self,
        bill_id: str,
        event_type: str,
        error_message: str,
        recipient: str | None = None,
    ) -> NotificationLog:
        """Record a failed SMS send with the error detail."""
        log = NotificationLog(
            bill_id=bill_id,
            type="SMS",
            event_type=event_type,
            recipient=recipient,
            status="failed",
            error_message=error_message,
        )
        return await self.create(log)