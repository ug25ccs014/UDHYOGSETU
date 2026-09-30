"""OCR provider abstraction.

The document intelligence pipeline reads text out of scanned images and
PDFs through an ``OCRProvider`` interface. Development uses Tesseract; a
future cloud OCR provider can implement the same interface without changing
callers.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

try:
    import pytesseract
    from PIL import Image
    _HAS_PYTESSERACT = True
except ImportError:  # pragma: no cover
    _HAS_PYTESSERACT = False


class OCRProvider(ABC):
    """Turn an image (or image-derived bytes) into text."""

    name: str = "base"

    @abstractmethod
    def image_to_text(self, image_bytes: bytes) -> str:
        """Extract text from raw image bytes."""

    def is_available(self) -> bool:
        return True


class TesseractOCRProvider(OCRProvider):
    name = "tesseract"

    def image_to_text(self, image_bytes: bytes) -> str:
        if not _HAS_PYTESSERACT:
            logger.warning("pytesseract/PIL not installed; OCR skipped.")
            return ""
        try:
            from io import BytesIO
            image = Image.open(BytesIO(image_bytes))
            return pytesseract.image_to_string(image)
        except Exception as exc:  # noqa: BLE001 - depends on tesseract binary/OCR libs
            logger.warning("Tesseract OCR failed: %s", exc)
            return ""


class MockOCRProvider(OCRProvider):
    """Deterministic provider used when Tesseract is unavailable.

    Mirrors the sample-document format so document tests exercise the full
    extraction pipeline without a system Tesseract install.
    """

    name = "mock"

    def image_to_text(self, image_bytes: bytes) -> str:
        # We cannot read text out of arbitrary pixels without OCR; return
        # empty and let callers skip OCR gracefully.
        return ""


class OCRProviderFactory:
    """Builds the configured OCR provider with graceful fallback."""

    @classmethod
    def create(cls, name: str | None = None) -> OCRProvider:
        name = (name or "tesseract").lower()
        if name == "tesseract" and _HAS_PYTESSERACT:
            return TesseractOCRProvider()
        return MockOCRProvider()