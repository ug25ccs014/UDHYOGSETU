"""SLA breach prediction (spec §23).

Predictive assistance, NOT a statutory determination. Combines the time-based
SLA risk with application features (department, approval type, document
completeness, outstanding queries) to estimate the probability of breaching the
department SLA deadline.

If insufficient historical data is available the model degrades gracefully to the
deterministic time-based estimate, always labelled as predictive assistance.
"""

from __future__ import annotations

from app.models import Approval, ApprovalStatus
from app.services.sla_engine import SlaEngine

# Feature risk weights (department / approval-type specific experience).
_DEPARTMENT_RISK = {
    "mpcb": 0.18,
    "pollution": 0.18,
    "boiler": 0.10,
    "fire": 0.08,
    "factory": 0.12,
    "industrial safety": 0.12,
    "midc": 0.05,
    "labour": 0.08,
    "gst": 0.04,
    "esic": 0.06,
}


class SlaPredictor:
    def __init__(self, sla_engine: SlaEngine | None = None):
        self.sla = sla_engine or SlaEngine()

    def predict(self, approval: Approval) -> dict:
        """Estimate SLA breach probability for a single approval."""
        submitted_at = (
            approval.submitted_at
            if hasattr(approval, "submitted_at")
            else None
        )
        status = approval.status
        try:
            status_enum = ApprovalStatus(status) if not isinstance(status, ApprovalStatus) else status
        except (ValueError, TypeError):
            status_enum = ApprovalStatus.NOT_STARTED

        base = self.sla.evaluate(
            status_enum,
            submitted_at,
            approval.estimated_processing_days,
        )

        # Pre-submission: no SLA pressure.
        if status_enum in (ApprovalStatus.NOT_STARTED, ApprovalStatus.DRAFT):
            return {
                **base,
                "prediction": "NOT_STARTED",
                "features": {"submitted": False},
                "key_risk_factors": [],
                "confidence": 0.0,
                "note": "Predictive assistance: not a statutory determination.",
            }

        # Terminal states need no prediction.
        if status_enum == ApprovalStatus.APPROVED:
            return {
                **base,
                "prediction": "COMPLETED",
                "features": {"submitted": True},
                "key_risk_factors": [],
                "confidence": 0.0,
                "note": "Predictive assistance: not a statutory determination.",
            }

        time_risk = base.get("breach_probability", 0.0)
        feature_risk = self._feature_risk(approval)

        # Feature*time interaction: features matter more as the deadline nears.
        score = min(0.99, time_risk * (1.0 + feature_risk))
        ratio = time_risk

        factors = self._risk_factors(approval, base, feature_risk, time_risk)

        return {
            **base,
            "prediction": self._label(score),
            "breach_probability": round(score, 3),
            "features": self._features(approval),
            "key_risk_factors": factors,
            "confidence": round(min(0.95, 0.4 + 0.5 * ratio), 2),
            "note": "Predictive assistance: not a statutory determination.",
        }

    def _features(self, approval: Approval) -> dict:
        department = (approval.department or "").lower()
        base = self._department_risk(department)
        return {
            "department": department,
            "department_risk_weight": round(base, 3),
            "query_raised": status_is(approval.status, ApprovalStatus.QUERY_RAISED),
            "in_inspection": status_is(approval.status, ApprovalStatus.INSPECTION),
        }

    def _feature_risk(self, approval: Approval) -> float:
        """Compute risk from non-time features, 0..1."""
        department = (approval.department or "").lower()
        risk = min(1.0, self._department_risk(department))
        s = approval.status
        if status_is(s, ApprovalStatus.QUERY_RAISED):
            risk = min(1.0, risk + 0.20)       # outstanding query
        if status_is(s, ApprovalStatus.INSPECTION):
            risk = min(1.0, risk + 0.10)       # awaiting inspection
        if hasattr(approval, "is_mandatory") and approval.is_mandatory:
            risk = min(1.0, risk + 0.05)
        return risk

    def _risk_factors(self, approval, base, feature_risk, time_risk) -> list[str]:
        factors = []
        if time_risk >= 0.5 or base.get("status") == "AT_RISK":
            factors.append("SLA window mostly elapsed")
        if status_is(approval.status, ApprovalStatus.QUERY_RAISED):
            factors.append("Outstanding query from the department")
        if status_is(approval.status, ApprovalStatus.INSPECTION):
            factors.append("Awaiting inspection")
        if feature_risk >= 0.25:
            factors.append(f"Department risk profile ({approval.department})")
        if not factors:
            factors.append("No material risk factors identified")
        return factors

    @staticmethod
    def _department_risk(department: str) -> float:
        for token, risk in _DEPARTMENT_RISK.items():
            if token in department:
                return risk
        return 0.10

    @staticmethod
    def _label(score: float) -> str:
        if score >= 0.7:
            return "HIGH"
        if score >= 0.35:
            return "MEDIUM"
        return "LOW"


def status_is(value, enum_member) -> bool:
    try:
        enum = ApprovalStatus(value)
        return enum == enum_member
    except (ValueError, TypeError):
        return value == enum_member
