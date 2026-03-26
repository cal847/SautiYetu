"""
app/ai/analysis_service.py
---------------------------
Public interface for AI-powered bill analysis.

Entry point
-----------
    insight = await analyze_bill(parsed_bill, title="KE-2024-012")

The function:
  1. Builds the prompt from the parsed bill text
  2. Calls DeepInfra via DeepInfraClient
  3. Parses + validates the JSON response with AIInsightResponse
  4. Retries up to MAX_RETRIES times on transient failures
  5. Returns an AIInsightCreate ready for InsightRepository.upsert()
"""

import json
import logging
from dataclasses import dataclass

from pydantic import ValidationError

from app.ai.client import DeepInfraClient, DeepInfraError
from app.ai.prompts.bill_analysis import build_bill_analysis_prompt
from app.ai.schemas.insight_schema import AIInsightCreate, AIInsightResponse
from app.config import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


# ── Custom exception ──────────────────────────────────────────────────────────

class AIAnalysisError(Exception):
    """
    Raised when the AI service cannot produce a valid insight after
    all retry attempts have been exhausted.
    """


# ── Input model ───────────────────────────────────────────────────────────────

@dataclass
class ParsedBill:
    """
    Minimal representation of a parsed bill passed into analyze_bill().
    Mirrors app/parser/models.py — kept here as a local dataclass so
    this module has no circular import with the parser layer.
    """
    title: str
    title: str
    raw_text: str


# ── Core function ─────────────────────────────────────────────────────────────

async def analyze_bill(parsed_bill: ParsedBill) -> AIInsightCreate:
    """
    Analyse a parsed bill with DeepInfra and return a validated AIInsightCreate.

    Retry behaviour
    ---------------
    - Retries up to MAX_RETRIES (2) times on DeepInfraError or JSON/validation errors.
    - On each retry the same prompt is resent — the LLM is stateless.
    - After all attempts are exhausted, raises AIAnalysisError.

    Args:
        parsed_bill: A ParsedBill with at minimum title, title, raw_text.

    Returns:
        AIInsightCreate — validated insight data ready for DB persistence.

    Raises:
        AIAnalysisError: When no valid response is produced after retries.
    """
    prompt = build_bill_analysis_prompt(
        bill=f"Title: {parsed_bill.title}\n\n{parsed_bill.raw_text}"
    )

    last_error: Exception | None = None

    async with DeepInfraClient() as client:
        for attempt in range(1, MAX_RETRIES + 2):  # attempts: 1, 2, 3
            try:
                logger.info(
                    "AI analysis attempt %d/%d title=%s",
                    attempt,
                    MAX_RETRIES + 1,
                    parsed_bill.title,
                )

                raw_text = await client.chat(prompt)
                insight_response = _parse_and_validate(raw_text)

                result = AIInsightCreate(
                    title=parsed_bill.title,
                    model_used=client.model,
                    **insight_response.model_dump(),
                )

                logger.info(
                    "AI analysis succeeded title=%s model=%s",
                    parsed_bill.title,
                    client.model,
                )
                return result

            except (DeepInfraError, AIAnalysisError, ValidationError, json.JSONDecodeError) as exc:
                last_error = exc
                logger.warning(
                    "AI analysis attempt %d failed title=%s error=%s",
                    attempt,
                    parsed_bill.title,
                    str(exc)[:200],
                )

    raise AIAnalysisError(
        f"AI analysis failed for title={parsed_bill.title!r} "
        f"after {MAX_RETRIES + 1} attempts. Last error: {last_error}"
    ) from last_error


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_and_validate(raw_text: str) -> AIInsightResponse:
    """
    Strip any accidental markdown fences, parse JSON, and validate
    against AIInsightResponse.

    Raises:
        json.JSONDecodeError: If the text is not valid JSON after stripping.
        ValidationError:      If the JSON does not match AIInsightResponse.
    """
    cleaned = _strip_markdown_fences(raw_text)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise json.JSONDecodeError(
            f"LLM returned non-JSON output: {cleaned[:300]}", exc.doc, exc.pos
        ) from exc

    return AIInsightResponse.model_validate(data)


def _strip_markdown_fences(text: str) -> str:
    """
    Remove ```json ... ``` or ``` ... ``` wrappers the LLM may add
    despite being told not to.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        # drop opening fence (```json or ```) and closing fence (```)
        inner_lines = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        return "\n".join(inner_lines).strip()
    return stripped