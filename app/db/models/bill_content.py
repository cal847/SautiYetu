from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BillContent(Base):
    __tablename__ = "bill_content"

    bill_id: Mapped[str] = mapped_column(
        ForeignKey("bills.id", ondelete="CASCADE"),
        primary_key=True,
        comment="FK to bills.id — one-to-one",
    )
    raw_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full extracted text from PDF or HTML source",
    )
    parsed_sections: Mapped[dict | list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Structured section breakdown: [{title, body, clause_number}]",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    bill: Mapped["Bill"] = relationship(  # noqa: F821
        "Bill",
        back_populates="content",
    )

    def __repr__(self) -> str:
        preview = (self.raw_text or "")[:60].replace("\n", " ")
        return f"<BillContent bill_id={self.bill_id!r} preview={preview!r}>"