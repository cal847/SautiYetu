from typing import Dict, Any
import json


# =========================
# VERSION TAG (important for tracking)
# =========================
PROMPT_VERSION = "v1.0"


# =========================
# PROMPT COMPONENTS
# =========================

SUMMARY_PROMPT = """
Summary
Explain the bill in plain English as if speaking to an informed non-lawyer.
Max 5 sentences, active voice, under 150 words total.
Answer: What does this bill do? Why was it introduced? What changes?
"""

ECONOMIC_IMPACT_PROMPT = """
Economic Impact
Describe who gains, who bears costs, and how.
Mention fiscal effects: revenue, spending, taxes, compliance costs.
Keep to 2-3 concise sentences.
"""

SECTOR_IMPACT_PROMPT = """
Sector Impact
List only sectors explicitly mentioned or directly affected.
Use lowercase, singular form.
Return as a JSON array.
Return [] if none.
"""

RISK_FLAGS_PROMPT = """
Risk Flags
Identify concerns: implementation challenges, unintended consequences, equity issues.
Use short phrases (max 5 words each).
Return as a JSON array.
Return [] if none.
"""

PUBLIC_PARTICIPATION_PROMPT = """
Public Participation
Return true ONLY if the bill explicitly requires public participation.
Otherwise return false.
Do not infer.
"""


# =========================
# MASTER PROMPT TEMPLATE
# =========================

BILL_ANALYSIS_PROMPT = """
You are a senior legal and policy analyst.

Task:
Analyze the provided bill and generate structured output matching the AIInsight model.

Output Requirements:
- Return ONLY valid JSON
- No markdown, no explanations
- Follow this schema exactly:

{{
  "summary": string | null,
  "economic_impact": string | null,
  "sector_impact": string[],
  "risk_flags": string[],
  "public_participation": boolean
}}

Rules:
- If missing info → use null or empty arrays
- Do NOT infer
- Keep responses concise and factual

Field Instructions:
{summary}

{economic}

{sector}

{risk}

{participation}

Bill JSON:
{bill}
"""


# =========================
# BUILDER FUNCTION
# =========================

def build_bill_analysis_prompt(bill: str) -> str:
    """
    Combines all prompt components into one final prompt string.

    Args:
        bill (dict): The bill data

    Returns:
        str: Final prompt string ready for LLM
    """

    return BILL_ANALYSIS_PROMPT.format(
        summary=SUMMARY_PROMPT.strip(),
        economic=ECONOMIC_IMPACT_PROMPT.strip(),
        sector=SECTOR_IMPACT_PROMPT.strip(),
        risk=RISK_FLAGS_PROMPT.strip(),
        participation=PUBLIC_PARTICIPATION_PROMPT.strip(),
        bill=bill.strip(),
    )