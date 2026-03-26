# app/parser/models.py

from pydantic import BaseModel
from typing import List, Optional


class BillSection(BaseModel):
    heading: str
    content: str
    clause_number: Optional[str] = None


class ParsedBill(BaseModel):
    bill_id: str
    title: str
    raw_text: str
    sections: List[BillSection]