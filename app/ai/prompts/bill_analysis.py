"""
app/ai/prompts/bill_analysis.py
--------------------------------
Versioned prompt templates for bill analysis.
Each dimension has its own constant; BILL_ANALYSIS_PROMPT
assembles them into the final LLM prompt via build_bill_analysis_prompt().
"""

PROMPT_VERSION = "v1.0"


# ── Field-level instructions ──────────────────────────────────────────────────

SUMMARY_PROMPT = """
Summary
Explain the bill in plain English as if speaking to an informed non-lawyer.
Use active voice and provide a comprehensive overview.
Answer: What does this bill do? Why was it introduced? What changes?
"""

ECONOMIC_IMPACT_PROMPT = """
Economic Impact
Describe who gains, who bears costs, and how comprehensively.
Mention all fiscal effects: revenue, spending, taxes, compliance costs, and economic implications.
"""

SECTOR_IMPACT_PROMPT = """
Sector Impact
List all sectors explicitly mentioned or directly affected.
Use lowercase, singular form.
Return as a JSON array.
Return [] if none.
"""

RISK_FLAGS_PROMPT = """
Risk Flags
Identify all concerns: implementation challenges, unintended consequences, equity issues, and potential risks.
Use clear phrases to describe each concern.
Return as a JSON array.
Return [] if none.
"""

PUBLIC_PARTICIPATION_PROMPT = """
Public Participation
Return true ONLY if the bill explicitly requires public participation.
Otherwise return false.
Do not infer.
"""


# ── Master template ───────────────────────────────────────────────────────────
# NOTE: uses {{}} for literal braces in the JSON schema example so that
# .format() does not treat them as substitution targets.

BILL_ANALYSIS_PROMPT = """
You are a senior legal and policy analyst.

Task:
Analyze the provided bill and generate structured output matching the AIInsight model.

Output Requirements:
- Return ONLY valid JSON
- No markdown, no explanations outside the JSON
- Follow this schema exactly:

{{
  "summary": string | null,
  "economic_impact": string | null,
  "sector_impact": string[],
  "risk_flags": string[],
  "public_participation": boolean
}}

Rules:
- If information is missing or unclear → use null or empty arrays
- Do NOT infer — only use what is explicitly stated in the bill
- Keep responses concise and factual

Field Instructions:
{summary}

{economic}

{sector}

{risk}

{participation}

Bill Text:
{bill}
"""


# ── Builder ───────────────────────────────────────────────────────────────────

def build_bill_analysis_prompt(bill: str) -> str:
    """
    Assemble all prompt components into the final prompt string.

    Args:
        bill: Raw bill text extracted by the parser service.

    Returns:
        Fully formatted prompt string ready to send to the LLM.
    """
    return BILL_ANALYSIS_PROMPT.format(
        summary=SUMMARY_PROMPT.strip(),
        economic=ECONOMIC_IMPACT_PROMPT.strip(),
        sector=SECTOR_IMPACT_PROMPT.strip(),
        risk=RISK_FLAGS_PROMPT.strip(),
        participation=PUBLIC_PARTICIPATION_PROMPT.strip(),
        bill=bill.strip(),  # fixed: was bill_json=, but template key is {bill}
    )