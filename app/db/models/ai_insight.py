from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AIInsight(Base):
    __tablename__ = "ai_insights"

    bill_id: Mapped[str] = mapped_column(
        ForeignKey("bills.id", ondelete="CASCADE"),
        primary_key=True,
        comment="FK to bills.id — one-to-one",
    )
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Plain-English summary of the bill",
    )
    economic_impact: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Narrative describing economic consequences",
    )
    sector_impact: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment='Affected sectors e.g. ["finance", "health", "agriculture"]',
    )
    risk_flags: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment='Notable risks or concerns e.g. ["increased taxation", "reduced subsidies"]',
    )
    public_participation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True when bill explicitly requires public participation",
    )
    model_used: Mapped[str | None] = mapped_column(
        nullable=True,
        comment="DeepInfra model identifier used for this analysis",
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
    bill: Mapped["Bill"] = relationship(  # noqa: F821
        "Bill",
        back_populates="ai_insight",
    )

    def __repr__(self) -> str:
        return (
            f"<AIInsight bill_id={self.bill_id!r} "
            f"public_participation={self.public_participation}>"
        )