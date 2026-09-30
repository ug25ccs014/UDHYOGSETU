"""Tests for the SLA breach predictor (spec §23)."""

from datetime import datetime, timedelta, timezone

from app.models import ApprovalStatus
from app.services.sla_predictor import SlaPredictor


class _FakeApproval:
    def __init__(self, status, submitted_at, department="gst", sla_days=60, is_mandatory=False):
        self.status = status
        self.submitted_at = submitted_at
        self.estimated_processing_days = sla_days
        self.department = department
        self.is_mandatory = is_mandatory


NOW = datetime.now(timezone.utc)


def test_not_started_returns_not_started_prediction():
    result = SlaPredictor().predict(_FakeApproval(ApprovalStatus.NOT_STARTED, None))
    assert result["prediction"] == "NOT_STARTED"
    assert result["confidence"] == 0.0


def test_approved_returns_completed():
    result = SlaPredictor().predict(_FakeApproval(ApprovalStatus.APPROVED, NOW - timedelta(days=40)))
    assert result["prediction"] == "COMPLETED"


def test_early_submission_is_low_risk():
    result = SlaPredictor().predict(_FakeApproval(ApprovalStatus.SUBMITTED, NOW - timedelta(days=3)))
    assert result["prediction"] == "LOW"


def test_breach_probability_rises_as_deadline_nears():
    early = SlaPredictor().predict(_FakeApproval(ApprovalStatus.SUBMITTED, NOW - timedelta(days=2)))
    late = SlaPredictor().predict(_FakeApproval(ApprovalStatus.SUBMITTED, NOW - timedelta(days=58)))
    assert late["breach_probability"] > early["breach_probability"]
    assert late["prediction"] in ("MEDIUM", "HIGH")


def test_query_raised_flags_risk_factor():
    result = SlaPredictor().predict(
        _FakeApproval(ApprovalStatus.QUERY_RAISED, NOW - timedelta(days=20), department="mpcb")
    )
    joined = " ".join(result["key_risk_factors"]).lower()
    assert "query" in joined


def test_high_risk_department_scores_higher_than_low_risk():
    mpcb = SlaPredictor().predict(
        _FakeApproval(ApprovalStatus.SUBMITTED, NOW - timedelta(days=30), department="mpcb")
    )
    gst = SlaPredictor().predict(
        _FakeApproval(ApprovalStatus.SUBMITTED, NOW - timedelta(days=30), department="gst")
    )
    assert mpcb["breach_probability"] > gst["breach_probability"]
