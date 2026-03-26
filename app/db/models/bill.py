import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Bill ID from parliament (e.g. 'National Assembly Bill No. 12 of 2024')",
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="introduced | passed | rejected | withdrawn",
    )
    category: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="finance | health | education | security | etc.",
    )
    date_introduced: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_passed: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_url: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        unique=True,
        comment="Canonical URL of the source document on parliament.go.ke",
    )
    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="SHA-256 of raw document — used for deduplication",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    content: Mapped["BillContent | None"] = relationship(  # noqa: F821
        "BillContent",
        back_populates="bill",
        uselist=False,
        cascade="all, delete-orphan",
    )
    ai_insight: Mapped["AIInsight | None"] = relationship(  # noqa: F821
        "AIInsight",
        back_populates="bill",
        uselist=False,
        cascade="all, delete-orphan",
    )
    notification_logs: Mapped[list["NotificationLog"]] = relationship(  # noqa: F821
        "NotificationLog",
        back_populates="bill",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Bill id={self.id!r} status={self.status!r}>"