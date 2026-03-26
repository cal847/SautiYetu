# tests/parser/test_pdf_parser.py

import io
import pytest
import requests
from app.parser.pdf_parser import parse_pdf
from app.parser.exceptions import ParserError

# Kenya Finance Bill 2024 — publicly available from parliament.go.ke
FINANCE_BILL_URL = "https://parliament.go.ke/sites/default/files/2024-05/Finance%20Bill%2C%202024_0.pdf"


@pytest.fixture(scope="module")
def finance_bill_bytes():
    """Download the Finance Bill PDF once and reuse across tests."""
    response = requests.get(FINANCE_BILL_URL, timeout=30)
    assert response.status_code == 200, f"Could not fetch bill PDF: {response.status_code}"
    return response.content


def test_parse_valid_pdf(finance_bill_bytes):
    result = parse_pdf(finance_bill_bytes, "BILL123")

    assert result.title is not None
    assert len(result.sections) >= 1
    assert result.raw_text is not None


def test_parse_pdf_bytes(finance_bill_bytes):
    result = parse_pdf(finance_bill_bytes, "BILL123")

    assert result.bill_id == "BILL123"


def test_invalid_pdf():
    with pytest.raises(ParserError):
        parse_pdf(b"this is not a pdf", "BILL123")


def test_empty_pdf():
    with pytest.raises(ParserError):
        parse_pdf(b"", "BILL123")