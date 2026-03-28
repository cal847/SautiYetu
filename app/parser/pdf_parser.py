# app/parser/pdf_parser.py

import io
import os
import base64
import requests
import pdfplumber
import logging
from typing import Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import time

from app.parser.models import ParsedBill, BillSection
from app.parser.section_extractor import extract_title, extract_sections
from app.parser.exceptions import ParserError

# Configure logging
logger = logging.getLogger(__name__)

# DPI for rendering pages to images before sending to DeepInfra.
# Lower = smaller payload = faster + less likely to timeout.
# 72 DPI is very low quality but extremely fast and small payloads for testing
_OCR_RESOLUTION = 72
_OCR_TIMEOUT = 30  # Reduced timeout for faster failure recovery
_BATCH_SIZE = 1  # Reduce to 1 to avoid rate limiting during testing

# Connection pooling configuration
_ADAPTER_CONFIG = {
    'pool_connections': 5,
    'pool_maxsize': 10,
    'max_retries': Retry(total=1, backoff_factor=0.1)  # Reduced retries for testing
}

# Session for connection reuse
_session = None
def get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.mount('https://', HTTPAdapter(**_ADAPTER_CONFIG))
        _session.mount('http://', HTTPAdapter(**_ADAPTER_CONFIG))
    return _session


# ── URL fetching ──────────────────────────────────────────────────────────────

def _fetch_from_url(url: str) -> bytes:
    logger.info(f"Fetching PDF from URL: {url}")
    try:
        response = get_session().get(url, timeout=30)
        response.raise_for_status()
        logger.info(f"Successfully fetched {len(response.content)} bytes from URL")
        return response.content
    except requests.RequestException as e:
        logger.error(f"Failed to fetch PDF from URL: {str(e)}")
        raise ParserError(f"Failed to fetch PDF from URL: {str(e)}")


# ── PDF opening ───────────────────────────────────────────────────────────────

def _open_pdf(file: Union[str, bytes]):
    """
    Accepts:
      - A URL string (https://...)  → fetches bytes then opens
      - A file path string          → opens directly
      - Raw bytes                   → wraps in BytesIO
    """
    logger.info(f"Opening PDF from type: {type(file).__name__}")
    
    try:
        if isinstance(file, str):
            if file.startswith("http://") or file.startswith("https://"):
                pdf_bytes = _fetch_from_url(file)
                logger.info("Opening PDF from fetched bytes")
                return pdfplumber.open(io.BytesIO(pdf_bytes))
            else:
                logger.info(f"Opening PDF from file path: {file}")
                return pdfplumber.open(file)

        elif isinstance(file, bytes):
            if len(file) == 0:
                raise ParserError("Empty PDF bytes provided")
            logger.info(f"Opening PDF from {len(file)} bytes")
            return pdfplumber.open(io.BytesIO(file))

        else:
            raise ParserError("Invalid input: expected URL string, file path, or bytes")

    except ParserError:
        raise
    except Exception as e:
        logger.error(f"Failed to open PDF: {str(e)}")
        raise ParserError(f"Failed to open PDF: {str(e)}")


def _is_encrypted(pdf) -> bool:
    try:
        encrypted = bool(pdf.doc.encryption)
        logger.info(f"PDF encryption status: {'encrypted' if encrypted else 'not encrypted'}")
        return encrypted
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
        logger.warning("DEEPINFRA_API_KEY is not set, OCR will be skipped")
        return None
    logger.debug("DeepInfra API key retrieved successfully")
    return key


def _get_deepinfra_ocr_model() -> str:
    try:
        from app.config import settings
        return settings.deepinfra_ocr_model
    except (ImportError, AttributeError):
        return os.environ.get(
            "DEEPINFRA_OCR_MODEL",
            "allenai/olmOCR-2-7B-1025"
        )


def _get_deepinfra_text_model() -> str:
    try:
        from app.config import settings
        return settings.deepinfra_text_model
    except (ImportError, AttributeError):
        return os.environ.get(
            "DEEPINFRA_TEXT_MODEL",
            "meta-llama/Llama-3.2-11B-Vision-Instruct"
        )


# ── DeepInfra vision OCR ──────────────────────────────────────────────────────

def _render_page_to_base64(page) -> str:
    """Render a PDF page to a base64-encoded PNG at _OCR_RESOLUTION DPI."""
    logger.debug(f"Rendering page {page.page_number} to base64 image")
    img = page.to_image(resolution=_OCR_RESOLUTION).original
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    logger.debug(f"Page {page.page_number} rendered to {len(b64_str)} characters base64 string")
    return b64_str


def _ocr_page_with_deepinfra_ocr_model(page, page_num: int) -> tuple[int, str]:
    """
    Render the page to a PNG and send it to DeepInfra's specialized OCR model.
    """
    logger.info(f"Starting OCR for page {page_num} using specialized OCR model")
    start_time = time.time()
    
    api_key = _get_deepinfra_api_key()
    if not api_key:
        logger.warning(f"No API key provided, skipping OCR for page {page_num}")
        return page_num, ""
    
    model = _get_deepinfra_ocr_model()
    b64_image = _render_page_to_base64(page)

    payload = {
        "model": model,
        "max_tokens": 1024,  # Further reduced for faster processing
        "temperature": 0.1,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"image/png;base64,{b64_image}"
                        }
                    }
                ]
            }
        ]
    }

    try:
        logger.debug(f"Sending OCR request for page {page_num}, model: {model}")
        response = get_session().post(
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
        result = data["choices"][0]["message"]["content"].strip()
        
        duration = time.time() - start_time
        logger.info(f"OCR completed for page {page_num} in {duration:.2f}s, got {len(result)} chars")
        
        return page_num, result

    except requests.exceptions.Timeout:
        duration = time.time() - start_time
        logger.error(f"OCR timed out for page {page_num} after {duration:.2f}s")
        raise ParserError(
            f"DeepInfra OCR timed out after {_OCR_TIMEOUT}s."
        )
    except requests.RequestException as e:
        duration = time.time() - start_time
        status_code = getattr(e.response, 'status_code', 'unknown')
        logger.error(f"OCR request failed for page {page_num} after {duration:.2f}s with status {status_code}: {str(e)}")
        raise ParserError(f"DeepInfra OCR request failed with status {status_code}: {str(e)}")
    except (KeyError, IndexError) as e:
        duration = time.time() - start_time
        logger.error(f"Unexpected OCR response format for page {page_num} after {duration:.2f}s: {str(e)}")
        raise ParserError(f"Unexpected DeepInfra response format: {str(e)}")


def _ocr_page_with_deepinfra_text_model(page, page_num: int) -> tuple[int, str]:
    """
    Render the page to a PNG and send it to DeepInfra's general vision model.
    """
    logger.info(f"Starting OCR for page {page_num} using general vision model")
    start_time = time.time()
    
    api_key = _get_deepinfra_api_key()
    if not api_key:
        logger.warning(f"No API key provided, skipping OCR for page {page_num}")
        return page_num, ""
    
    model = _get_deepinfra_text_model()
    b64_image = _render_page_to_base64(page)

    payload = {
        "model": model,
        "max_tokens": 1024,  # Further reduced for faster processing
        "temperature": 0.1,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"image/png;base64,{b64_image}"
                        }
                    },
                    {
                        "type": "text",
                        "text": (
                            "Extract text from document. No comments, just text."
                        )
                    }
                ]
            }
        ]
    }

    try:
        logger.debug(f"Sending general vision request for page {page_num}, model: {model}")
        response = get_session().post(
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
        result = data["choices"][0]["message"]["content"].strip()
        
        duration = time.time() - start_time
        logger.info(f"General vision OCR completed for page {page_num} in {duration:.2f}s, got {len(result)} chars")
        
        return page_num, result

    except requests.exceptions.Timeout:
        duration = time.time() - start_time
        logger.error(f"General vision OCR timed out for page {page_num} after {duration:.2f}s")
        raise ParserError(
            f"DeepInfra OCR timed out after {_OCR_TIMEOUT}s."
        )
    except requests.RequestException as e:
        duration = time.time() - start_time
        status_code = getattr(e.response, 'status_code', 'unknown')
        logger.error(f"General vision OCR request failed for page {page_num} after {duration:.2f}s with status {status_code}: {str(e)}")
        raise ParserError(f"DeepInfra OCR request failed with status {status_code}: {str(e)}")
    except (KeyError, IndexError) as e:
        duration = time.time() - start_time
        logger.error(f"Unexpected general vision response format for page {page_num} after {duration:.2f}s: {str(e)}")
        raise ParserError(f"Unexpected DeepInfra response format: {str(e)}")


# ── Per-page extraction ───────────────────────────────────────────────────────

def _extract_single_page_text(page) -> tuple[int, str]:
    """
    Extract text from a single page with detailed logging.
    Returns tuple of (page_number, extracted_text).
    """
    page_num = page.page_number
    logger.info(f"Starting extraction for page {page_num}")
    
    # Attempt 1: word-level (handles multi-column layout)
    logger.debug(f"Attempting word-level extraction for page {page_num}")
    words = page.extract_words()
    if words:
        logger.debug(f"Found {len(words)} words for page {page_num}, sorting...")
        words_sorted = sorted(words, key=lambda w: (round(w["top"] / 10) * 10, w["x0"]))
        result = " ".join(word["text"] for word in words_sorted)
        logger.info(f"Word-level extraction successful for page {page_num}, got {len(result)} chars")
        return page_num, result

    # Attempt 2: plain text extraction
    logger.debug(f"Attempting plain text extraction for page {page_num}")
    text = page.extract_text()
    if text and text.strip():
        result = text.strip()
        logger.info(f"Plain text extraction successful for page {page_num}, got {len(result)} chars")
        return page_num, result

    # Attempt 3: DeepInfra specialized OCR model (for scanned pages)
    logger.info(f"Using DeepInfra specialized OCR for page {page_num}")
    try:
        page_num, ocr_result = _ocr_page_with_deepinfra_ocr_model(page, page_num)
        if ocr_result.strip():
            logger.info(f"Specialized OCR successful for page {page_num}")
            return page_num, ocr_result
        else:
            logger.warning(f"Specialized OCR returned empty result for page {page_num}, trying general model")
    except ParserError as e:
        logger.warning(f"Specialized OCR failed for page {page_num}: {str(e)}, trying general model")

    # Attempt 4: DeepInfra general vision model with specific instructions
    logger.info(f"Using DeepInfra general vision model for page {page_num}")
    try:
        page_num, ocr_result = _ocr_page_with_deepinfra_text_model(page, page_num)
        if ocr_result.strip():
            logger.info(f"General vision OCR successful for page {page_num}")
            return page_num, ocr_result
        else:
            logger.warning(f"General vision OCR returned empty result for page {page_num}")
    except ParserError as e:
        logger.warning(f"General vision OCR failed for page {page_num}: {str(e)}")

    # Final fallback: return empty string if all OCR methods failed
    logger.warning(f"All extraction methods failed for page {page_num}, returning empty string")
    return page_num, ""


def _extract_all_pages_text_parallel(pages) -> list:
    """
    Extract text from all pages using thread pool for parallel processing.
    """
    total_pages = len(pages)
    logger.info(f"Starting parallel extraction for {total_pages} pages with {_BATCH_SIZE} concurrent workers")
    
    results = [None] * len(pages)  # Pre-allocate results list

    # Process in batches to avoid overwhelming the API
    for start_idx in range(0, total_pages, _BATCH_SIZE):
        end_idx = min(start_idx + _BATCH_SIZE, total_pages)
        batch_pages = pages[start_idx:end_idx]
        batch_indices = list(range(start_idx, end_idx))

        logger.info(f"Processing batch {start_idx//_BATCH_SIZE + 1}/{(total_pages+_BATCH_SIZE-1)//_BATCH_SIZE}")

        with ThreadPoolExecutor(max_workers=_BATCH_SIZE) as executor:
            # Submit batch tasks
            future_to_batch_idx = {
                executor.submit(_extract_single_page_text, page): idx 
                for idx, page in zip(batch_indices, batch_pages)
            }

            # Collect results as they complete
            for future in as_completed(future_to_batch_idx):
                page_idx = future_to_batch_idx[future]
                try:
                    page_num, extracted_text = future.result()
                    results[page_idx] = extracted_text

                    completed_count = sum(1 for r in results if r is not None)
                    logger.info(f"Progress: {completed_count}/{total_pages} pages completed")

                except Exception as e:
                    page_num = pages[page_idx].page_number
                    logger.error(f"Failed to extract page {page_num}: {str(e)}")
                    raise ParserError(f"Failed to extract page {page_num}: {str(e)}")

    logger.info(f"All {len(pages)} pages extracted successfully")
    return results


# ── Full document extraction ──────────────────────────────────────────────────

def _extract_text(pdf) -> str:
    logger.info(f"Starting text extraction for PDF with {len(pdf.pages)} pages")
    
    if _is_encrypted(pdf):
        logger.error("PDF is encrypted")
        raise ParserError("Encrypted PDF not supported")

    try:
        pages = pdf.pages
        
        # For small PDFs or those with clear text, process sequentially
        if len(pages) <= 2:
            logger.info("Small PDF detected, processing sequentially")
            pages_text = []
            for page in pages:
                _, page_text = _extract_single_page_text(page)
                if page_text and page_text.strip():  # Only add non-empty text
                    pages_text.append(page_text)
        else:
            # For larger PDFs, use parallel processing with batches
            logger.info("Large PDF detected, using batched parallel processing")
            pages_text = _extract_all_pages_text_parallel(pages)
            # Filter out empty results after processing
            pages_text = [text for text in pages_text if text and text.strip()]
        
        full_text = "\n".join(pages_text).strip()

        if not full_text:
            logger.warning("No readable text found in entire document, returning empty string")
            return ""

        logger.info(f"Extraction completed successfully: {len(full_text)} characters")
        return full_text

    except ParserError:
        raise
    except Exception as e:
        logger.error(f"Text extraction failed: {str(e)}")
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
    start_time = time.time()
    logger.info(f"Starting PDF parsing for bill ID: {bill_id}")
    
    pdf = _open_pdf(file)

    try:
        raw_text = _extract_text(pdf)
        logger.info("Starting title extraction")
        
        # Only extract title if we have text
        if raw_text:
            title = extract_title(raw_text)
            logger.info(f"Title extracted: '{title[:50]}...'")  # Show first 50 chars
        else:
            logger.warning("No text available, using fallback title")
            title = "Untitled Document"
        
        logger.info("Starting section extraction")
        sections = extract_sections(raw_text) if raw_text else []
        
        if not sections:
            logger.warning("No sections found, creating single full-text section")
            sections = [
                BillSection(
                    heading="Full Text",
                    content=raw_text,
                    clause_number=None
                )
            ]

        duration = time.time() - start_time
        logger.info(f"PDF parsing completed for bill {bill_id} in {duration:.2f}s")
        
        return ParsedBill(
            bill_id=bill_id,
            title=title,
            raw_text=raw_text,
            sections=sections
        )

    finally:
        pdf.close()
        logger.info(f"PDF closed for bill ID: {bill_id}")

# Cleanup session on module exit
import atexit
atexit.register(lambda: _session.close() if _session else None)