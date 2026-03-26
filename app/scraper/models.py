from pydantic import BaseModel
from typing import Optional


class ScrapedBill(BaseModel):
    title: str
    pdf_url: Optional[str]