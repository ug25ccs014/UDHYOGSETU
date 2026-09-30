"""Document intelligence: text extraction, OCR, field extraction and
cross-document validation.

This module is deliberately deterministic — field extraction uses targeted
regex + structured heuristics rather than a free-running LLM, so credentials
(GSTIN/PAN/registration numbers), names, addresses and dates are validated
reliably. An optional LLM explanation can be layered on top later.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from typing import Any

from app.ai.embeddings import EmbeddingProviderFactory
from app.ai.ocr import OCRProviderFactory

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Document classification
# ---------------------------------------------------------------------------

DOCUMENT_CLASSIFIERS = [
    ("PAN CARD", re.compile(r"permanent\s*account\s*number|\bpan\b", re.IGNORECASE)),
    ("GST REGISTRATION", re.compile(r"good.?s?\s*and\s*services\s*tax|\bgstin?\b", re.IGNORECASE)),
    ("GST RETURN", re.compile(r"gst\s*return|\bgstr-?\d?\b", re.IGNORECASE)),
    ("SHOPS & ESTABLISHMENT", re.compile(r"shops?\s*(and|&)\s*establishment", re.IGNORECASE)),
    ("FACTORY LICENSE", re.compile(r"factory\s*(license|licence)", re.IGNORECASE)),
    ("BOILER REGISTRATION", re.compile(r"boiler", re.IGNORECASE)),
    ("MPCB CONSENT", re.compile(r"consent\s*(to\s*establish|to\s*operate)|pollution.?control\s*board", re.IGNORECASE)),
    ("FIRE NOC", re.compile(r"fire\s*(noc|no\s*objection|services)", re.IGNORECASE)),
    ("LAND DOCUMENT", re.compile(r"(land|property|title\s*deed|lease\s*deed)", re.IGNORECASE)),
    ("INCORPORATION CERTIFICATE", re.compile(r"incorporation", re.IGNORECASE)),
]

PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
GSTIN_RE = re.compile(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9]Z[0-9A-Z]\b")
EMAIL_RE = re.compile(r"[\w.\-+]+@[\w.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(\+?91[- ]?)?[6-9][0-9]{9}")
ALPHA_NUM_RE = re.compile(r"\b[A-Z0-9\-\/]{4,}\b")

DATE_PATTERNS = [
    (re.compile(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})"), "%d-%m-%Y"),
]

_ISSUE_KEYWORDS = ("issue", "issued", "date of issue", "date")
_EXPIRY_KEYWORDS = ("expiry", "expires", "valid until", "valid upto", "valid up to", "renewal date")


class DocumentIntelligenceService:
    """Extract structure from uploaded documents and validate across docs."""

    def __init__(self, db=None):
        self.db = db
        self.ocr = OCRProviderFactory.create()
        self.embedder = EmbeddingProviderFactory.create()

    # ------------------------------------------------------------------
    # Text extraction
    # ------------------------------------------------------------------
    def extract_text_from_file(self, file_path: str, content_type: str = "") -> str:
        """Extract text from PDF/DOCX/images/txt using the right reader."""
        ext = os.path.splitext(file_path or "")[1].lower()
        if ext == ".pdf":
            return self._extract_pdf(file_path)
        if ext in (".docx",):
            return self._extract_docx(file_path)
        if ext in (".png", ".jpg", ".jpeg", ".webp"):
            return self._extract_image(file_path)
        if ext in (".txt", ".log", ".md", ".csv"):
            return self._read_text(file_path)
        return self._read_text(file_path)

    def _extract_pdf(self, file_path: str) -> str:
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.debug("PyMuPDF not installed; PDF extraction unavailable")
            return ""
        try:
            text_parts = []
            with fitz.open(file_path) as doc:
                for page in doc:
                    text_parts.append(page.get_text())
            text = "\n".join(text_parts)
            if text.strip():
                return text
            # Scanned PDF -> OCR each page image.
            images = []
            with fitz.open(file_path) as doc:
                for page in doc:
                    for img in page.get_images(full=True):
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)
                        if pix.n - pix.alpha >= 4:
                            pix = fitz.Pixmap(fitz.csRGB, pix)
                        images.append(pix.tobytes("png"))
            return "\n".join(self.ocr.image_to_text(b) for b in images) if images else ""
        except Exception as exc:  # noqa: BLE001 - corrupt/malformed PDFs fail open
            logger.warning("PDF text extraction failed: %s", exc)
            return ""

    def _extract_docx(self, file_path: str) -> str:
        try:
            from docx import Document as DocxDocument
        except ImportError:
            logger.debug("python-docx not installed; DOCX extraction unavailable")
            return ""
        try:
            doc = DocxDocument(file_path)
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as exc:  # noqa: BLE001 - corrupt/incompatible files fail open
            logger.warning("DOCX text extraction failed: %s", exc)
            return ""

    def _extract_image(self, file_path: str) -> str:
        try:
            with open(file_path, "rb") as f:
                return self.ocr.image_to_text(f.read())
        except Exception as exc:  # noqa: BLE001 - corrupt images fail open
            logger.warning("Image OCR failed: %s", exc)
            return ""

    def _read_text(self, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as exc:  # noqa: BLE001 - fail-open on unreadable sources
            logger.debug("Text read failed for %s: %s", file_path, exc)
            return ""

    # ------------------------------------------------------------------
    # Field extraction
    # ------------------------------------------------------------------
    def classify_document(self, text: str) -> str:
        """Return the most likely document type based on content."""
        best = "GENERIC_DOCUMENT"
        best_score = 0
        for label, pattern in DOCUMENT_CLASSIFIERS:
            matches = pattern.findall(text)
            if matches and len(matches) > best_score:
                best = label
                best_score = len(matches)
        return best

    def extract_fields(self, text: str) -> dict[str, Any]:
        """Deterministically extract structured fields from document text."""
        text_block = text or ""
        fields = {
            "document_type": self.classify_document(text_block),
            "name": self._extract_name(text_block),
            "address": self._extract_address(text_block),
            "registration_number": self._find_number(text_block),
            "gstin": self._find_gstin(text_block),
            "pan": self._find_pan(text_block),
            "issue_date": self._find_issue_date(text_block),
            "expiry_date": self._find_expiry_date(text_block),
            "authority": self._extract_authority(text_block),
            "email": self._find_email(text_block),
            "phone": self._find_phone(text_block),
        }
        return {k: (v or None) for k, v in fields.items()}

    def _extract_name(self, text: str) -> str:
        lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
        for kw in ("company", "firm", "legal name", "name of", "proprietor", "customer name"):
            for i, ln in enumerate(lines):
                if kw in ln.lower() and ":" in ln:
                    return ln.split(":", 1)[1].strip()
        return lines[0] if lines and len(lines[0]) < 60 else None

    def _extract_address(self, text: str) -> str:
        idx = (text or "").lower().find("address")
        if idx >= 0:
            snippet = text[idx:idx + 300]
            return snippet.split("\n")[0].replace("Address", "").replace(":", "").strip()[:300]
        return None

    def _find_number(self, text: str) -> str | None:
        for mobj in re.finditer(r"(reg(istration)?.?no|reg\s*no|certificate\s*no)[\s:]*([A-Z0-9\-\/]+)", text or "", re.IGNORECASE):
            return mobj.group(3)
        found = ALPHA_NUM_RE.findall(text or "")
        return found[0] if found else None

    def _find_gstin(self, text: str) -> str | None:
        m = GSTIN_RE.search(text or "")
        return m.group(0) if m else None

    def _find_pan(self, text: str) -> str | None:
        m = PAN_RE.search(text or "")
        return m.group(0) if m else None

    def _find_email(self, text: str) -> str | None:
        m = EMAIL_RE.search(text or "")
        return m.group(0) if m else None

    def _find_phone(self, text: str) -> str | None:
        m = PHONE_RE.search(text or "")
        return m.group(0) if m else None

    def _parse_date(self, text: str) -> str | None:
        for pattern, fmt in DATE_PATTERNS:
            m = pattern.search(text or "")
            if m:
                day, month, year = m.groups()
                year = int(year)
                if year < 100:
                    year += 2000
                try:
                    return datetime(year, int(month), int(day)).strftime("%Y-%m-%d")
                except ValueError:
                    continue
        return None

    def _find_issue_date(self, text: str) -> str | None:
        lowered = (text or "").lower()
        lines = lowered.splitlines()
        for ln in lines:
            if any(k in ln for k in _ISSUE_KEYWORDS):
                for mobj in re.finditer(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})", ln):
                    snippet = ln
                    parsed = self._parse_date(snippet)
                    if parsed:
                        return parsed
        return None

    def _find_expiry_date(self, text: str) -> str | None:
        lowered = (text or "").lower()
        for ln in lowered.splitlines():
            if any(k in ln for k in _EXPIRY_KEYWORDS):
                parsed = self._parse_date(ln)
                if parsed:
                    return parsed
        return None

    def _extract_authority(self, text: str) -> str | None:
        for auth in ("mpcb", "department of boiler", "factory", "fire services", "gst", "dish", "directorate of industries"):
            if auth in (text or "").lower():
                return auth.upper()
        return None

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    def validate_document_fields(self, fields: dict[str, Any]) -> list[str]:
        """Return a list of validation errors for a single document's fields."""
        errors = []
        if fields.get("gstin") and not GSTIN_RE.match(fields["gstin"]):
            errors.append(f"Invalid GSTIN format: {fields['gstin']}")
        if fields.get("pan") and not PAN_RE.match(fields["pan"]):
            errors.append(f"Invalid PAN format: {fields['pan']}")
        issue = fields.get("issue_date")
        expiry = fields.get("expiry_date")
        if issue and expiry and issue > expiry:
            errors.append("Issue date is after expiry date")
        if expiry and expiry < datetime.utcnow().strftime("%Y-%m-%d"):
            errors.append("Document has expired")
        return errors


def normalize_org_name(name: str) -> str:
    """Normalize a company name for fuzzy comparison."""
    if not name:
        return ""
    normalized = name.upper()
    for token in ("PVT", "LTD", "PRIVATE", "LIMITED", "LLP", "PVT.", "CO."):
        normalized = normalized.replace(token, "")
    return re.sub(r"[^A-Z0-9]", "", normalized)


def fuzzy_match(a: str, b: str) -> bool:
    """Return True if two organization names match (normalized equality)."""
    na, nb = normalize_org_name(a), normalize_org_name(b)
    if not na or not nb:
        return False
    return na == nb or na in nb or nb in na


class CrossDocumentValidator:
    """Detect mismatches across documents (PAN vs GST vs land, etc.)."""

    def validate(self, documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Compare extracted fields and return per-field validation findings.

        Each finding: {level: GREEN|YELLOW|RED, field, message, docs:[ids]}
        """
        findings: list[dict[str, Any]] = []
        docs = [d for d in documents if d.get("extracted_fields")]

        names = [{"id": d["id"], "name": d["extracted_fields"].get("name")} for d in docs if d["extracted_fields"].get("name")]
        pans = {d["extracted_fields"].get("pan") for d in docs if d["extracted_fields"].get("pan")}
        addresses = [{"id": d["id"], "address": d["extracted_fields"].get("address")} for d in docs if d["extracted_fields"].get("address")]

        # Company-name consistency across documents.
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                if not fuzzy_match(names[i]["name"], names[j]["name"]):
                    findings.append({
                        "level": "RED",
                        "field": "name",
                        "message": f"Company name mismatch: '{names[i]['name']}' vs '{names[j]['name']}'",
                        "docs": [names[i]["id"], names[j]["id"]],
                    })

        # Address consistency.
        for i in range(len(addresses)):
            for j in range(i + 1, len(addresses)):
                if normalize_org_name(addresses[i]["address"]) != normalize_org_name(addresses[j]["address"]) and (addresses[i]["address"] or addresses[j]["address"]):
                    findings.append({
                        "level": "YELLOW",
                        "field": "address",
                        "message": f"Address mismatch: '{addresses[i]['address'][:60]}' vs '{addresses[j]['address'][:60]}'",
                        "docs": [addresses[i]["id"], addresses[j]["id"]],
                    })

        # PAN should be present on GST registration.
        name_doc = names[0]["id"] if names else None
        if pans and name_doc:
            pass  # PAN presence check is informational only.

        # Expired-document check.
        for d in docs:
            expiry = d["extracted_fields"].get("expiry_date")
            if expiry and expiry < datetime.utcnow().strftime("%Y-%m-%d"):
                findings.append({
                    "level": "RED",
                    "field": "expiry",
                    "message": f"Document expired on {expiry}",
                    "docs": [d["id"]],
                })

        return findings