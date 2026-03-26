"""
app/ai/schemas/insight_schema.py
---------------------------------
Pydantic models for validating and structuring the AI analysis response.

AIInsightResponse  — validates the raw JSON returned by the LLM.
AIInsightCreate    — the dict passed to InsightRepository.upsert().
"""

from pydantic import BaseModel, Field, field_validator


class AIInsightResponse(BaseModel):
    """
    Strict schema for the JSON object the LLM must return.
    Missing optional fields fall back to safe defaults so a partial
    response never crashes the pipeline.
    """

    summary: str | None = Field(
        default=None,
        description="Plain-English summary of the bill (≤150 words).",
    )
    economic_impact: str | None = Field(
        default=None,
        description="Narrative of fiscal and economic consequences.",
    )
    sector_impact: list[str] = Field(
        default_factory=list,
        description="Lowercase, singular sector names affected by the bill.",
    )
    risk_flags: list[str] = Field(
        default_factory=list,
        description="Short phrases (≤5 words) flagging concerns or risks.",
    )
    public_participation: bool = Field(
        default=False,
        description="True only when the bill explicitly requires public participation.",
    )

    @field_validator("sector_impact", "risk_flags", mode="before")
    @classmethod
    def ensure_list(cls, v: object) -> list:
        """Coerce None or non-list values to an empty list."""
        if v is None:
            return []
        if not isinstance(v, list):
            return []
        return v

    @field_validator("summary", "economic_impact", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: object) -> str | None:
        """Treat empty strings as null."""
        if isinstance(v, str) and not v.strip():
            return None
        return v  # type: ignore[return-value]


class AIInsightCreate(AIInsightResponse):
    """
    Extends the response schema with the bill_id and model metadata
    needed to persist the record via InsightRepository.
    """

    bill_id: str
    model_used: str | None = None

    def to_db_dict(self) -> dict:
        """Return a plain dict suitable for ORM model construction."""
        return self.model_dump()