# app/parser/section_extractor.py

import re
from typing import List
from app.parser.models import BillSection


def extract_title(text: str) -> str:
    lines = text.split("\n")

    for line in lines:
        clean = line.strip()
        if clean:
            return clean

    return "Untitled Bill"


def extract_sections(text: str) -> List[BillSection]:
    """
    Extract sections using common legislative patterns:
    Clause 1, Clause 2, PART I, SCHEDULE
    """

    pattern = r"(Clause\s+\d+.*?)(?=Clause\s+\d+|SCHEDULE|PART\s+[IVX]+|$)"

    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)

    sections = []

    for match in matches:
        lines = match.strip().split("\n")
        heading = lines[0].strip()
        content = "\n".join(lines[1:]).strip()

        # Extract clause number
        clause_match = re.search(r"Clause\s+(\d+)", heading, re.IGNORECASE)
        clause_number = clause_match.group(1) if clause_match else None

        sections.append(
            BillSection(
                heading=heading,
                content=content,
                clause_number=clause_number
            )
        )

    return sections