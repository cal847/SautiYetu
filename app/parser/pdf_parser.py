# app/parser/pdf_parser.py

import io
import os
import base64
import requests
import pdfplumber
from typing import Union

from app.parser.models import ParsedBill, BillSection
from app.parser.section_extractor import extract_title, extract_sections
from app.parser.exceptions import ParserError

# DPI for rendering pages to images before sending to DeepInfra.
# Lower = smaller payload = faster + less likely to timeout.
# 150 DPI is sufficient for OCR on A4 legislative documents.
_OCR_RESOLUTION = 150
_OCR_TIMEOUT = 120  # seconds — vision models take longer than text models


# ── URL fetching ──────────────────────────────────────────────────────────────

def _fetch_from_url(url: str) -> bytes:
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        raise ParserError(f"Failed to fetch PDF from URL: {str(e)}")


# ── PDF opening ───────────────────────────────────────────────────────────────

def _open_pdf(file: Union[str, bytes]):
    """
    Accepts:
      - A URL string (https://...)  → fetches bytes then opens
      - A file path string          → opens directly
      - Raw bytes                   → wraps in BytesIO
    """
    try:
        if isinstance(file, str):
            if file.startswith("http://") or file.startswith("https://"):
                pdf_bytes = _fetch_from_url(file)
                return pdfplumber.open(io.BytesIO(pdf_bytes))
            else:
                return pdfplumber.open(file)

        elif isinstance(file, bytes):
            if len(file) == 0:
                raise ParserError("Empty PDF bytes provided")
            return pdfplumber.open(io.BytesIO(file))

        else:
            raise ParserError("Invalid input: expected URL string, file path, or bytes")

    except ParserError:
        raise
    except Exception as e:
        raise ParserError(f"Failed to open PDF: {str(e)}")


def _is_encrypted(pdf) -> bool:
    try:
        return bool(pdf.doc.encryption)
    except AttributeError:
        return False


# ── DeepInfra config helpers ──────────────────────────────────────────────────

def _get_deepinfra_api_key() -> str:
    try:
        from app.config import settings
        key = settings.deepinfra_api_key
    except (ImportError, AttributeError):
        key = os.environ.get("DEEPINFRA_API_KEY", "")

    if not key:
        raise ParserError(
            "DEEPINFRA_API_KEY is not set. "
            "Add it to your .env file: DEEPINFRA_API_KEY=your_key_here"
        )
    return key


def _get_deepinfra_model() -> str:
    try:
        from app.config import settings
        return settings.deepinfra_model
    except (ImportError, AttributeError):
        return os.environ.get(
            "DEEPINFRA_MODEL",
            "meta-llama/Llama-3.2-11B-Vision-Instruct"
        )


# ── DeepInfra vision OCR ──────────────────────────────────────────────────────

def _render_page_to_base64(page) -> str:
    """Render a PDF page to a base64-encoded PNG at _OCR_RESOLUTION DPI."""
    img = page.to_image(resolution=_OCR_RESOLUTION).original
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _ocr_page_with_deepinfra(page) -> str:
    """
    Render the page to a PNG and send it to DeepInfra's vision model.
    Used only when pdfplumber cannot extract text (scanned / image-based PDF).
    """
    api_key = _get_deepinfra_api_key()
    model = _get_deepinfra_model()
    b64_image = _render_page_to_base64(page)

    payload = {
        "model": model,
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{b64_image}"
                        }
                    },
                    {
                        "type": "text",
                        "text": (
                            "You are a document transcription assistant. "
                            "Extract ALL text from this page of a Kenyan parliamentary bill exactly as it appears. "
                            "Preserve clause numbers, section headings, and paragraph structure. "
                            "Output only the extracted text — no commentary, no markdown formatting."
                        )
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(
            "https://api.deepinfra.com/v1/openai/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=_OCR_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    except requests.exceptions.Timeout:
        raise ParserError(
            f"DeepInfra OCR timed out after {_OCR_TIMEOUT}s. "
            "The page image may be too large — try reducing _OCR_RESOLUTION."
        )
    except requests.RequestException as e:
        raise ParserError(f"DeepInfra OCR request failed: {str(e)}")
    except (KeyError, IndexError) as e:
        raise ParserError(f"Unexpected DeepInfra response format: {str(e)}")


# ── Per-page extraction ───────────────────────────────────────────────────────

def _extract_page_text(page) -> str:
    """
    1. Try word-level extraction  — best for multi-column text PDFs.
    2. Fall back to extract_text() — for simpler text PDFs.
    3. Fall back to DeepInfra vision OCR — for scanned / image-based PDFs.
    """
    # Attempt 1: word-level (handles multi-column layout)
    words = page.extract_words()
    if words:
        words_sorted = sorted(words, key=lambda w: (round(w["top"] / 10) * 10, w["x0"]))
        return " ".join(word["text"] for word in words_sorted)

    # Attempt 2: plain text extraction
    text = page.extract_text()
    if text and text.strip():
        return text.strip()

    # Attempt 3: DeepInfra vision OCR (scanned page)
    return _ocr_page_with_deepinfra(page)


# ── Full document extraction ──────────────────────────────────────────────────

def _extract_text(pdf) -> str:
    if _is_encrypted(pdf):
        raise ParserError("Encrypted PDF not supported")

    try:
        pages_text = []

        for page in pdf.pages:
            page_text = _extract_page_text(page)
            if page_text:
                pages_text.append(page_text)

        full_text = "\n".join(pages_text).strip()

        if not full_text:
            raise ParserError("No readable text found")

        return full_text

    except ParserError:
        raise
    except Exception as e:
        raise ParserError(f"Text extraction failed: {str(e)}")


# ── Public API ────────────────────────────────────────────────────────────────

def parse_pdf(file: Union[str, bytes], bill_id: str) -> ParsedBill:
    """
    Parse a PDF bill from a URL, file path, or raw bytes.

    Args:
        file:    URL string (https://...), local file path, or PDF bytes
        bill_id: Unique identifier for this bill

    Returns:
        ParsedBill with title, sections, and raw_text

    Raises:
        ParserError on unreadable, encrypted, or invalid input
    """
    pdf = _open_pdf(file)

    try:
        raw_text = _extract_text(pdf)
        title = extract_title(raw_text)
        sections = extract_sections(raw_text)

        if not sections:
            sections = [
                BillSection(
                    heading="Full Text",
                    content=raw_text,
                    clause_number=None
                )
            ]

        return ParsedBill(
            bill_id=bill_id,
            title=title,
            raw_text=raw_text,
            sections=sections
        )

    finally:
        pdf.close()