import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class NotificationLog(Base):
    __tablename__ = "notification_log"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    bill_id: Mapped[str] = mapped_column(
        ForeignKey("bills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="SMS",
        comment="Notification channel — always SMS for now",
    )
    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="bill_passed | public_participation",
    )
    recipient: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="Phone number the SMS was sent to",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="success | failed",
    )
    error_message: Mapped[str | None] = mapped_column(
        nullable=True,
        comment="Error detail when status=failed",
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    bill: Mapped["Bill"] = relationship(  # noqa: F821
        "Bill",
        back_populates="notification_logs",
    )

    def __repr__(self) -> str:
        return (
            f"<NotificationLog bill_id={self.bill_id!r} "
            f"event={self.event_type!r} status={self.status!r}>"
        )