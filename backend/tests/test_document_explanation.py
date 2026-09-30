"""Tests for AI document explanations (spec §16)."""


from app.services.document_explanation import DocumentExplanationService


async def test_explain_empty_findings():
    result = await DocumentExplanationService().explain_findings([])
    assert result["summary"]
    assert result["items"] == []


async def test_explain_red_expiry_finding():
    findings = [{
        "level": "RED",
        "field": "expiry",
        "message": "Document expired on 2025-01-01",
        "docs": ["doc-1"],
    }]
    result = await DocumentExplanationService().explain_findings(findings)
    assert result["summary"]
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["severity"] == "RED"
    # Deterministic action mentions renewal for the expiry finding.
    assert "renew" in item["action"].lower() or "corrected" in item["action"].lower()


async def test_explain_name_mismatch_finding():
    findings = [{
        "level": "RED",
        "field": "name",
        "message": "Company name mismatch: 'ABC' vs 'XYZ'",
        "docs": ["a", "b"],
    }]
    result = await DocumentExplanationService().explain_findings(findings)
    item = result["items"][0]
    assert item["field"] == "name"
    assert "legal name" in item["action"].lower()


async def test_explain_summary_counts():
    findings = [
        {"level": "RED", "field": "name", "message": "x"},
        {"level": "YELLOW", "field": "address", "message": "y"},
    ]
    result = await DocumentExplanationService().explain_findings(findings)
    assert "critical" in result["summary"].lower()
