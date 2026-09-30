"""Application workflow engine (state machine) — spec §21.

Models the governed lifecycle of an industrial approval application as a
deterministic state machine so transitions are explicit, validated, and
full of side effects (audit + notifications) rather than ad-hoc status edits.

States and allowed transitions:

    NOT_STARTED -> DRAFT
    DRAFT       -> SUBMITTED | CANCELED
    SUBMITTED   -> UNDER_REVIEW | QUERY_RAISED | REJECTED
    UNDER_REVIEW-> INSPECTION | QUERY_RAISED | APPROVED | REJECTED
    QUERY_RAISED-> SUBMITTED | APPROVED | REJECTED   (re-apply after answering)
    INSPECTION  -> APPROVED | REJECTED | QUERY_RAISED
    APPROVED    -> EXPIRED                             (renewal)
    CANCELED    -> NOT_STARTED                         (re-open)
    EXPIRED     -> SUBMITTED                           (renewal re-application)

Terminal states: APPROVED, REJECTED, CANCELED.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.models import ApprovalStatus


@dataclass(frozen=True)
class Transition:
    from_status: ApprovalStatus
    to_status: ApprovalStatus
    label: str
    actor_roles: tuple = ("ENTREPRENEUR", "OFFICER", "ADMIN")
    side_effect: str = ""  # human description of what happens

    def __post_init__(self):
        object.__setattr__(self, "from_status", _coerce(self.from_status))
        object.__setattr__(self, "to_status", _coerce(self.to_status))


def _coerce(value) -> ApprovalStatus:
    if isinstance(value, ApprovalStatus):
        return value
    return ApprovalStatus[str(value).upper()]


# ---------------------------------------------------------------------------
# Workflow definition
# ---------------------------------------------------------------------------
APPROVED = ApprovalStatus.APPROVED
REJECTED = ApprovalStatus.REJECTED
CANCELED = ApprovalStatus.CANCELED

WORKFLOW: list[Transition] = [
    # Applicant-side
    Transition(ApprovalStatus.NOT_STARTED, ApprovalStatus.DRAFT, "Start application", ("ENTREPRENEUR", "OFFICER", "ADMIN")),
    Transition(ApprovalStatus.NOT_STARTED, ApprovalStatus.SUBMITTED, "Direct submit", ("ENTREPRENEUR", "OFFICER", "ADMIN")),
    Transition(ApprovalStatus.DRAFT, ApprovalStatus.SUBMITTED, "Submit application", ("ENTREPRENEUR", "OFFICER", "ADMIN")),
    Transition(ApprovalStatus.DRAFT, ApprovalStatus.CANCELED, "Cancel application", ("ENTREPRENEUR", "OFFICER", "ADMIN")),
    Transition(ApprovalStatus.CANCELED, ApprovalStatus.NOT_STARTED, "Re-open application", ("ENTREPRENEUR", "OFFICER", "ADMIN")),
    Transition(ApprovalStatus.SUBMITTED, ApprovalStatus.UNDER_REVIEW, "Begin review", ("OFFICER", "ADMIN")),
    Transition(ApprovalStatus.UNDER_REVIEW, ApprovalStatus.INSPECTION, "Schedule inspection", ("OFFICER", "ADMIN")),
    Transition(ApprovalStatus.UNDER_REVIEW, ApprovalStatus.QUERY_RAISED, "Raise query", ("OFFICER", "ADMIN")),
    Transition(ApprovalStatus.SUBMITTED, ApprovalStatus.QUERY_RAISED, "Raise query", ("OFFICER", "ADMIN")),
    Transition(ApprovalStatus.QUERY_RAISED, ApprovalStatus.SUBMITTED, "Resubmit with answer", ("ENTREPRENEUR",)),
    Transition(ApprovalStatus.INSPECTION, ApprovalStatus.APPROVED, "Approve after inspection", ("OFFICER", "ADMIN")),
    Transition(ApprovalStatus.UNDER_REVIEW, ApprovalStatus.APPROVED, "Approve", ("OFFICER", "ADMIN")),
    Transition(ApprovalStatus.QUERY_RAISED, ApprovalStatus.APPROVED, "Approve", ("OFFICER", "ADMIN")),
    Transition(ApprovalStatus.SUBMITTED, ApprovalStatus.APPROVED, "Approve", ("OFFICER", "ADMIN")),
    Transition(ApprovalStatus.INSPECTION, ApprovalStatus.REJECTED, "Reject", ("OFFICER", "ADMIN")),
    Transition(ApprovalStatus.UNDER_REVIEW, ApprovalStatus.REJECTED, "Reject", ("OFFICER", "ADMIN")),
    Transition(ApprovalStatus.QUERY_RAISED, ApprovalStatus.REJECTED, "Reject", ("OFFICER", "ADMIN")),
    Transition(ApprovalStatus.SUBMITTED, ApprovalStatus.REJECTED, "Reject", ("OFFICER", "ADMIN")),
    # Renewal / lifecycle
    Transition(ApprovalStatus.APPROVED, ApprovalStatus.EXPIRED, "Mark expired", ("ADMIN",)),
    Transition(ApprovalStatus.NOT_STARTED, ApprovalStatus.APPROVED, "Fast-track approval", ("ADMIN",)),
]

WORKFLOW_BY_FROM: dict = {}


def _build_index() -> None:
    WORKFLOW_BY_FROM.clear()
    for t in WORKFLOW:
        WORKFLOW_BY_FROM.setdefault(t.from_status, []).append(t)


_build_index()


class TransitionError(ValueError):
    """Raised when a requested transition is not allowed from the current state."""


@dataclass
class WorkflowDecision:
    """The result of attempting a transition."""
    allowed: bool
    requested: ApprovalStatus
    current_status: ApprovalStatus
    available: list[dict] = field(default_factory=list)
    error: str | None = None
    transition: Transition | None = None

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "requested": self.requested.value if self.requested else None,
            "current_status": self.current_status.value if self.current_status else None,
            "available": self.available,
            "error": self.error,
        }


class ApprovalWorkflowEngine:
    """Validates and applies application lifecycle transitions."""

    def __init__(self, actor_role: str = "ENTREPRENEUR"):
        self.actor_role = (actor_role or "ENTREPRENEUR").upper()

    def list_possible_transitions(self, current: ApprovalStatus) -> list[dict]:
        current = _coerce(current)
        return [
            {
                "to": t.to_status.value,
                "label": t.label,
                "side_effect": t.side_effect,
            }
            for t in WORKFLOW_BY_FROM.get(current, [])
            if self.actor_role in t.actor_roles
        ]

    def is_valid(self, current: ApprovalStatus, next_status: ApprovalStatus) -> bool:
        current = _coerce(current)
        next_status = _coerce(next_status)
        return any(
            t.to_status == next_status and self.actor_role in t.actor_roles
            for t in WORKFLOW_BY_FROM.get(current, [])
        )

    def decide(self, current: ApprovalStatus, requested: ApprovalStatus) -> WorkflowDecision:
        current = _coerce(current)
        requested = _coerce(requested)
        available = self.list_possible_transitions(current)
        if self.is_valid(current, requested):
            transition = next(t for t in WORKFLOW_BY_FROM.get(current, []) if t.to_status == requested)
            return WorkflowDecision(
                allowed=True,
                requested=requested,
                current_status=current,
                available=available,
                transition=transition,
            )
        return WorkflowDecision(
            allowed=False,
            requested=requested,
            current_status=current,
            available=available,
            error=(
                f"Transition {current.value} -> {requested.value} is not allowed "
                f"for role {self.actor_role}. Available: "
                + ", ".join(a["to"] for a in available) or "none"
            ),
        )

    def apply_side_effects(self, transition: Transition, approval) -> None:
        """Mutate an Approval object with the timestamps for this transition."""
        now = datetime.utcnow()
        to_enum = transition.to_status
        if to_enum is ApprovalStatus.APPROVED:
            approval.approved_at = approval.approved_at or now
        if to_enum is ApprovalStatus.SUBMITTED:
            approval.submitted_at = approval.submitted_at or now
        if to_enum is ApprovalStatus.EXPIRED:
            approval.is_active = False
        approval.status = to_enum

    def apply(self, approval, requested: ApprovalStatus, actor_role: str | None = None) -> WorkflowDecision:
        """Validate + apply a transition to an approval. Returns the decision,
        mutating ``approval`` only if allowed. The caller commits."""
        if actor_role is not None:
            self.actor_role = actor_role.upper()
        decision = self.decide(approval.status, requested)
        if decision.allowed and decision.transition:
            self.apply_side_effects(decision.transition, approval)
        return decision
