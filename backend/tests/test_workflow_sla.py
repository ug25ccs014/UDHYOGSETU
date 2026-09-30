"""Tests for the application workflow engine (spec §21) and SLA engine (spec §22)."""

from datetime import datetime, timedelta, timezone

from app.models import ApprovalStatus
from app.services.approval_workflow import ApprovalWorkflowEngine
from app.services.sla_engine import SlaEngine


class TestApprovalWorkflowEngine:
    def test_draft_to_submitted_allowed(self):
        engine = ApprovalWorkflowEngine("ENTREPRENEUR")
        decision = engine.decide(ApprovalStatus.DRAFT, ApprovalStatus.SUBMITTED)
        assert decision.allowed is True

    def test_not_started_to_submitted_via_direct_submit(self):
        engine = ApprovalWorkflowEngine("ENTREPRENEUR")
        assert engine.is_valid(ApprovalStatus.NOT_STARTED, ApprovalStatus.SUBMITTED)

    def test_invalid_transition_blocked(self):
        engine = ApprovalWorkflowEngine("ENTREPRENEUR")
        decision = engine.decide(ApprovalStatus.NOT_STARTED, ApprovalStatus.APPROVED)
        assert decision.allowed is False
        assert decision.error

    def test_entrepreneur_cannot_approve(self):
        engine = ApprovalWorkflowEngine("ENTREPRENEUR")
        decision = engine.decide(ApprovalStatus.UNDER_REVIEW, ApprovalStatus.APPROVED)
        assert decision.allowed is False

    def test_officer_can_approve_under_review(self):
        engine = ApprovalWorkflowEngine("OFFICER")
        decision = engine.decide(ApprovalStatus.UNDER_REVIEW, ApprovalStatus.APPROVED)
        assert decision.allowed is True

    def test_apply_sets_submitted_at(self):
        engine = ApprovalWorkflowEngine("ENTREPRENEUR")
        approval = _FakeApproval(ApprovalStatus.DRAFT)
        decision = engine.apply(approval, ApprovalStatus.SUBMITTED)
        assert decision.allowed is True
        assert approval.status.value == "SUBMITTED"
        assert approval.submitted_at is not None


class _FakeApproval:
    def __init__(self, status):
        self.status = status
        self.submitted_at = None
        self.approved_at = None
        self.is_active = True


class TestSlaEngine:
    def test_approved_is_completed(self):
        sla = SlaEngine().evaluate(ApprovalStatus.APPROVED, datetime.now(timezone.utc), 60)
        assert sla["status"] == "COMPLETED"

    def test_not_started_has_no_sla(self):
        sla = SlaEngine().evaluate(ApprovalStatus.NOT_STARTED, None, 60)
        assert sla["status"] == "NOT_STARTED"

    def test_on_track_early(self):
        ref = datetime.now(timezone.utc) - timedelta(days=10)
        sla = SlaEngine().evaluate(ApprovalStatus.SUBMITTED, ref, 60)
        assert sla["status"] == "ON_TRACK"

    def test_at_risk_at_80_percent(self):
        ref = datetime.now(timezone.utc) - timedelta(days=48)
        sla = SlaEngine().evaluate(ApprovalStatus.SUBMITTED, ref, 60)
        assert sla["status"] == "AT_RISK"

    def test_breached_when_over_deadline(self):
        ref = datetime.now(timezone.utc) - timedelta(days=70)
        sla = SlaEngine().evaluate(ApprovalStatus.SUBMITTED, ref, 60)
        assert sla["status"] == "BREACHED"

    def test_breach_probability_rises_with_ratio(self):
        ref_early = datetime.now(timezone.utc) - timedelta(days=5)
        ref_late = datetime.now(timezone.utc) - timedelta(days=55)
        e1 = SlaEngine().evaluate(ApprovalStatus.SUBMITTED, ref_early, 60)
        e2 = SlaEngine().evaluate(ApprovalStatus.SUBMITTED, ref_late, 60)
        assert e2["breach_probability"] > e1["breach_probability"]
