"""SLA engine — spec §22.

Computes the SLA health of an application based on elapsed time since
submission versus the department's stated processing deadline. It replaces the
ad-hoc logic that previously lived inline in the applications API with a
reusable service that also returns the specific risk reasons and a simple
probabilistic breach prediction.

SLA bands:
  * ON_TRACK  - < 75% of the SLA window elapsed
  * AT_RISK   - 75% - 100% elapsed
  * BREACHED  - > 100% elapsed (or past the deadline)
  * COMPLETED - the application reached a terminal success state (APPROVED)

The predicted breach probability is a deterministic logistic-style estimate
based on how much of the window has passed; it rises as the deadline
approaches.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import exp

from app.models import ApprovalStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_aware(value) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class SlaEngine:
    """Computes SLA status and breach probability for an application."""

    # The terminal "success" statuses that stop an SLA being breached.
    SUCCESS = frozenset({ApprovalStatus.APPROVED})

    def evaluate(
        self,
        status: str | ApprovalStatus,
        submitted_at: datetime | None,
        sla_days: int | None,
        reference_dt: datetime | None = None,
    ) -> dict:
        now = _coerce_aware(reference_dt) or _utcnow()
        try:
            status_enum = ApprovalStatus(status)
        except (ValueError, TypeError):
            status_enum = ApprovalStatus.NOT_STARTED
        sla_days = sla_days or 60

        if status_enum in self.SUCCESS:
            return self._complete(status_enum)

        reference = _coerce_aware(submitted_at) or now
        elapsed_days = max(0.0, (now - reference).total_seconds() / 86400.0)

        # If the application has not actually been submitted, there is no SLA.
        if status_enum in (ApprovalStatus.NOT_STARTED, ApprovalStatus.DRAFT):
            return {
                "status": "NOT_STARTED",
                "sla_days": sla_days,
                "days_elapsed": 0,
                "days_remaining": sla_days,
                "reason": "Application not yet submitted to the department.",
                "breach_probability": 0.0,
                "deadline": None,
            }

        ratio = elapsed_days / sla_days if sla_days else 1.0

        if ratio > 1.0:
            sla_status = "BREACHED"
            reason = (
                f"SLA breached — {elapsed_days:.0f} days elapsed against a "
                f"deadline of {sla_days} days."
            )
        elif ratio >= 0.75:
            sla_status = "AT_RISK"
            reason = (
                f"At risk — {elapsed_days:.0f} of {sla_days} days used "
                f"({ratio * 100:.0f}%). Escalate to the department officer."
            )
        else:
            sla_status = "ON_TRACK"
            reason = (
                f"On track — {elapsed_days:.0f} of {sla_days} days used."
            )

        breach_probability = self._breach_probability(ratio)
        deadline = reference + timedelta(days=sla_days)

        return {
            "status": sla_status,
            "sla_days": sla_days,
            "days_elapsed": round(elapsed_days, 1),
            "days_remaining": max(0.0, round(sla_days - elapsed_days, 1)),
            "reason": reason,
            "breach_probability": round(breach_probability, 3),
            "deadline": deadline.strftime("%Y-%m-%d"),
        }

    def _complete(self, status_enum: ApprovalStatus) -> dict:
        return {
            "status": "COMPLETED",
            "sla_days": 0,
            "days_elapsed": 0,
            "days_remaining": 0,
            "reason": "Application has reached a success state.",
            "breach_probability": 0.0,
            "deadline": None,
        }

    @staticmethod
    def _breach_probability(ratio: float) -> float:
        """Deterministic logistic-style breach estimate, 0 -> ~1 as ratio grows."""
        return 1.0 / (1.0 + exp(-8.0 * (ratio - 0.85)))
