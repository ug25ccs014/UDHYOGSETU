"""Officer application review API — list, inspect and act on applications.

The regular ``/applications`` endpoints are owner-scoped, so officers and admins
cannot resolve another entrepreneur's application through them. This router gives
officers/admins a review surface for the Explore flow (and the E2E lifecycle):

  * list applications (with entrepreneur + company context, filters),
  * inspect one application and its linked documents,
  * perform workflow transitions the officer role is allowed to make
    (SUBMITTED -> UNDER_REVIEW -> INSPECTION / QUERY_RAISED / APPROVED / REJECTED),
  * trigger a status sync against the tracked government system.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_officer
from app.core.database import get_db_session
from app.models import (
    Approval,
    ApprovalStatus,
    Document,
    GovernmentApplication,
    Project,
    User,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/officer/applications", tags=["officer-applications"])


async def _resolve_any_approval(db: AsyncSession, application_id: str) -> Approval:
    """Resolve an application by its government application_id or UUID."""
    result = await db.execute(
        select(Approval).where(Approval.application_id == application_id)
    )
    approval = result.scalar_one_or_none()

    if not approval:
        try:
            result = await db.execute(
                select(Approval).where(Approval.id == UUID(application_id))
            )
            approval = result.scalar_one_or_none()
        except (ValueError, AttributeError, TypeError):
            pass

    if not approval:
        raise HTTPException(status_code=404, detail="Application not found")
    return approval


def _officer_payload(approval: Approval, project: Project | None, owner: User | None) -> dict:
    return {
        "approval_id": str(approval.id),
        "application_id": approval.application_id or str(approval.id),
        "approval_name": approval.name,
        "department": approval.department,
        "risk_level": approval.risk_level,
        "is_mandatory": approval.is_mandatory,
        "estimated_processing_days": approval.estimated_processing_days,
        "status": approval.status.value if hasattr(approval.status, "value") else str(approval.status),
        "submitted_at": approval.submitted_at.isoformat() if approval.submitted_at else None,
        "approved_at": approval.approved_at.isoformat() if approval.approved_at else None,
        "source": approval.source,
        "owner_email": owner.email if owner else None,
        "owner_name": owner.name if owner else None,
        "company_name": project.company_name if project else None,
        "project_id": str(project.id) if project else None,
    }


async def _context(db: AsyncSession, approval: Approval) -> tuple[Project | None, User | None]:
    project = None
    owner = None
    result = await db.execute(select(Project).where(Project.id == approval.project_id))
    project = result.scalar_one_or_none()
    if project:
        result = await db.execute(select(User).where(User.id == project.user_id))
        owner = result.scalar_one_or_none()
    return project, owner


@router.get("")
async def list_applications(
    status: str | None = None,
    department: str | None = None,
    q: str | None = None,
    user: dict = Depends(require_officer),
    db: AsyncSession = Depends(get_db_session),
):
    """List applications across all entrepreneurs with optional filters."""
    stmt = select(Approval).order_by(Approval.updated_at.desc())
    if status:
        stmt = stmt.where(Approval.status == status.upper())
    if department:
        stmt = stmt.where(Approval.department.contains(department))
    result = await db.execute(stmt)
    approvals = list(result.scalars().all())

    items = []
    for approval in approvals:
        project, owner = await _context(db, approval)
        payload = _officer_payload(approval, project, owner)
        if q and q.lower() not in " ".join(
            str(payload.get(k) or "") for k in ("approval_name", "owner_email", "company_name")
        ).lower():
            continue
        items.append(payload)

    return {"applications": items}


@router.get("/{application_id}")
async def get_application(
    application_id: str,
    user: dict = Depends(require_officer),
    db: AsyncSession = Depends(get_db_session),
):
    """Application detail with entrepreneur + linked documents context."""
    approval = await _resolve_any_approval(db, application_id)
    project, owner = await _context(db, approval)
    result = await db.execute(select(Document).where(Document.project_id == approval.project_id))
    documents = [
        {
            "id": str(d.id),
            "file_name": d.file_name,
            "status": d.status.value if hasattr(d.status, "value") else str(d.status),
            "document_type": (d.custom_metadata or {}).get("document_type"),
        }
        for d in result.scalars().all()
    ]
    result = await db.execute(
        select(GovernmentApplication).where(GovernmentApplication.approval_id == approval.id)
    )
    gov_record = result.scalar_one_or_none()

    from app.services.approval_workflow import ApprovalWorkflowEngine

    engine = ApprovalWorkflowEngine("OFFICER")
    return {
        **_officer_payload(approval, project, owner),
        "documents": documents,
        "government": {
            "system": gov_record.system if gov_record else None,
            "government_application_id": gov_record.government_application_id if gov_record else None,
            "last_synced_status": gov_record.last_synced_status if gov_record else None,
        },
        "available_transitions": engine.list_possible_transitions(approval.status),
    }


@router.post("/{application_id}/transition")
async def transition_application(
    application_id: str,
    body: dict,
    user: dict = Depends(require_officer),
    db: AsyncSession = Depends(get_db_session),
):
    """Apply an officer-allowed workflow transition (SUB->PENDING_REVIEW etc.)."""
    approval = await _resolve_any_approval(db, application_id)
    target = (body or {}).get("to_status")
    if not target:
        raise HTTPException(status_code=400, detail="Missing 'to_status'")

    from app.services.approval_workflow import ApprovalWorkflowEngine

    try:
        requested = ApprovalStatus[target.upper()]
    except (KeyError, AttributeError) as exc:
        raise HTTPException(status_code=400, detail=f"Unknown status: {target}") from exc

    engine = ApprovalWorkflowEngine(user.get("role", "OFFICER"))
    decision = engine.apply(approval, requested)
    if not decision.allowed:
        raise HTTPException(status_code=400, detail=decision.error or "Transition not allowed")
    await db.commit()
    await db.refresh(approval)

    from app.audit.logging import log_audit

    try:
        await log_audit(
            db,
            user_id=user["sub"],
            action="approval.officer_transition",
            resource_type="approval",
            resource_id=str(approval.id),
            details={"from": decision.current_status.value, "to": requested.value},
        )
    except Exception as exc:  # noqa: BLE001 - audit side-channel must not break the transition
        logger.warning("Audit log failed for officer transition: %s", exc)
        await db.rollback()

    project, owner = await _context(db, approval)
    if owner:
        from app.notifications.service import NotificationService

        try:
            await NotificationService(db).create(
                str(owner.id),
                "Application Status Updated",
                f"Your application for {approval.name} is now {requested.value}.",
                category="approval",
                severity="info",
                project_id=approval.project_id,
                reference_id=str(approval.id),
            )
        except Exception as exc:  # noqa: BLE001 - notification side-channel must not break the transition
            logger.warning("Owner notification failed for officer transition: %s", exc)
            await db.rollback()

    return {**_officer_payload(approval, project, owner), "transition": decision.to_dict()}


@router.post("/{application_id}/sync")
async def sync_application(
    application_id: str,
    user: dict = Depends(require_officer),
    db: AsyncSession = Depends(get_db_session),
):
    """Reconcile one tracked application against its government system.

    For applications that were not tracked at submission time (e.g. checklist
    applications with no linked gateway), the first sync registers the
    application with the gateway system so later syncs can reconcile status."""
    approval = await _resolve_any_approval(db, application_id)
    from app.integrations.government_adapters import system_for_department
    from app.services.explore_service import ExploreService
    from app.services.gateway_service import GatewayService
    from app.services.gov_sync_service import GovSyncService

    result = await db.execute(
        select(GovernmentApplication).where(GovernmentApplication.approval_id == approval.id)
    )
    records = list(result.scalars().all())
    if not records:
        service = await ExploreService(db).find_service_for_approval(approval)
        system = (
            (service.gateway_system if service else None)
            or system_for_department(approval.department)
            or "maitri"
        )
        try:
            submission = await GatewayService().submit(
                system, {"sla_days": approval.estimated_processing_days or 30}
            )
        except Exception as exc:  # noqa: BLE001
            return {"approval_id": str(approval.id), "synced": 0, "items": [],
                    "error": f"Gateway unavailable ({exc})"}
        sub_data = (submission or {}).get("data") if isinstance((submission or {}).get("data"), dict) else {}
        gov_app_id = sub_data.get("application_id") or (submission or {}).get("application_id")
        if not gov_app_id:
            return {"approval_id": str(approval.id), "synced": 0, "items": [],
                    "error": "Could not register application with gateway"}
        record = await GovSyncService(db).track(approval, system, gov_app_id)
        records = [record]

    outcomes = [await GovSyncService(db).sync_one(r) for r in records]
    return {"approval_id": str(approval.id), "synced": len(outcomes), "items": outcomes}