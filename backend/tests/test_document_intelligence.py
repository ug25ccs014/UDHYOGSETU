"""Unit tests for the deterministic document-intelligence layer."""

import uuid

from app.services.document_intelligence import (
    CrossDocumentValidator,
    DocumentIntelligenceService,
    fuzzy_match,
)


def test_fuzzy_match_normalizes_names():
    assert fuzzy_match("ABC Textiles Private Limited", "ABC TEXTILES PVT LTD")
    assert fuzzy_match("ABC Textiles Pvt Ltd", "ABC TEXTILES PVT. LTD.")
    assert not fuzzy_match("ABC Textiles Pvt Ltd", "XYZ Textiles Pvt Ltd")


def test_classify_document():
    svc = DocumentIntelligenceService()
    assert svc.classify_document("This is the factory license for the premises") == "FACTORY LICENSE"
    assert svc.classify_document("good and services tax registration certificate") == "GST REGISTRATION"


def test_extract_pan_and_gstin():
    text = "Permanent Account Number: ABCDE1234F\nGSTIN: 27ABCDE1234F1Z5"
    svc = DocumentIntelligenceService()
    fields = svc.extract_fields(text)
    assert fields["pan"] == "ABCDE1234F"
    assert fields["gstin"] == "27ABCDE1234F1Z5"


def test_validate_fields_detects_bad_gstin():
    svc = DocumentIntelligenceService()
    errors = svc.validate_document_fields({"gstin": "not-a-gstin", "pan": "ABCDE1234F"})
    assert any("GSTIN" in e for e in errors)


def test_cross_document_name_mismatch_is_red():
    docs = [
        {"id": str(uuid.uuid4()), "name": "pan.pdf", "extracted_fields": {"name": "ABC Textiles Pvt Ltd"}},
        {"id": str(uuid.uuid4()), "name": "gst.pdf", "extracted_fields": {"name": "XYZ Textiles Pvt Ltd"}, "gstin": "27ABCDE1234F1Z5"},
    ]
    findings = CrossDocumentValidator().validate(docs)
    assert any(f["field"] == "name" and f["level"] == "RED" for f in findings)


def test_cross_document_no_mismatch_no_red():
    docs = [
        {"id": str(uuid.uuid4()), "name": "a.pdf", "extracted_fields": {"name": "ABC Textiles Pvt Ltd"}},
        {"id": str(uuid.uuid4()), "name": "b.pdf", "extracted_fields": {"name": "ABC Textiles Private Limited"}},
    ]
    findings = CrossDocumentValidator().validate(docs)
    assert not any(f["level"] == "RED" for f in findings)


def test_cross_document_expired_detected():
    docs = [
        {"id": str(uuid.uuid4()), "name": "expired.pdf", "extracted_fields": {"name": "ABC", "expiry_date": "2020-01-01"}},
    ]
    findings = CrossDocumentValidator().validate(docs)
    assert any(f["field"] == "expiry" and f["level"] == "RED" for f in findings)