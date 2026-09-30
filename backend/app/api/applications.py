import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models import Approval, ApprovalStatus, Document, Project
from app.services.project import ProjectService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["applications"])


async def _resolve_approval(db: AsyncSession, user: dict, application_id: str) -> Approval:
    """Find an approval by application_id or by UUID, verifying ownership."""
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

    service = ProjectService(db)
    project = await service.get_project(approval.project_id)
    if not project or str(project.user_id) != str(user["sub"]):
        raise HTTPException(status_code=403, detail="Not authorized to access this application")

    return approval


def _application_payload(approval: Approval, project: Project | None) -> dict:
    return {
        "application_id": approval.application_id or str(approval.id),
        "approval_name": approval.name,
        "department": approval.department,
        "project_name": project.name if project else None,
        "status": approval.status.value if hasattr(approval.status, "value") else str(approval.status),
        "submitted_at": approval.submitted_at.isoformat() if approval.submitted_at else None,
        "approved_at": approval.approved_at.isoformat() if approval.approved_at else None,
        "estimated_processing_days": approval.estimated_processing_days,
        "risk_level": approval.risk_level,
    }


@router.get("")
async def list_applications(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List applications for the authenticated user's projects"""
    service = ProjectService(db)
    projects = await service.list_user_projects(UUID(user["sub"]))
    project_map = {str(p.id): p for p in projects}

    if not projects:
        return {"applications": []}

    result = await db.execute(
        select(Approval).where(Approval.project_id.in_([p.id for p in projects]))
    )
    approvals = result.scalars().all()

    return {
        "applications": [
            _application_payload(a, project_map.get(str(a.project_id)))
            for a in approvals
        ]
    }


@router.get("/{application_id}")
async def get_application(
    application_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get application status and details"""
    approval = await _resolve_approval(db, user, application_id)
    service = ProjectService(db)
    project = await service.get_project(approval.project_id)
    return _application_payload(approval, project)


@router.post("/{application_id}/documents/{document_id}")
async def attach_application_document(
    application_id: str,
    document_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Attach one owned project document to an owned application."""
    approval = await _resolve_approval(db, user, application_id)
    document = (await db.execute(select(Document).where(Document.id == document_id))).scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if str(document.project_id) != str(approval.project_id):
        raise HTTPException(status_code=403, detail="Document does not belong to this application project")

    await db.refresh(approval, ["documents"])
    if not any(str(existing.id) == str(document.id) for existing in approval.documents):
        approval.documents.append(document)
        await db.commit()
    return {
        "application_id": approval.application_id or str(approval.id),
        "document_id": str(document.id),
        "attached": True,
    }


@router.delete("/{application_id}/documents/{document_id}")
async def detach_application_document(
    application_id: str,
    document_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Detach an owned project document from an owned application."""
    approval = await _resolve_approval(db, user, application_id)
    await db.refresh(approval, ["documents"])
    remaining = [document for document in approval.documents if str(document.id) != str(document_id)]
    if len(remaining) == len(approval.documents):
        raise HTTPException(status_code=404, detail="Document is not attached to this application")
    approval.documents = remaining
    await db.commit()
    return {
        "application_id": approval.application_id or str(approval.id),
        "document_id": str(document_id),
        "attached": False,
    }


@router.get("/{application_id}/sla")
async def get_sla_status(
    application_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get SLA status for application (spec §22)."""
    approval = await _resolve_approval(db, user, application_id)
    from app.services.sla_engine import SlaEngine
    sla = SlaEngine().evaluate(
        status=approval.status,
        submitted_at=approval.submitted_at,
        sla_days=approval.estimated_processing_days,
    )
    return {
        "application_id": approval.application_id or str(approval.id),
        "approval_name": approval.name,
        **sla,
    }


@router.get("/{application_id}/sla/prediction")
async def get_sla_prediction(
    application_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Predictive SLA breach estimate for an application (spec §23).

    This is predictive assistance combining time-based and feature-based risk;
    it is NOT a statutory determination.
    """
    approval = await _resolve_approval(db, user, application_id)
    from app.services.sla_predictor import SlaPredictor
    prediction = SlaPredictor().predict(approval)
    return {
        "application_id": approval.application_id or str(approval.id),
        "approval_name": approval.name,
        "predictive": True,
        **prediction,
    }


@router.get("/{application_id}/readiness")
async def get_submission_readiness(
    application_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Evaluate the application before entrepreneur submission.

    The result is a deterministic advisory readiness check over configured
    requirements, attached documents, profile data and document consistency.
    It does not contact government systems.
    """
    approval = await _resolve_approval(db, user, application_id)
    from app.services.submission_readiness import SubmissionReadinessService

    return await SubmissionReadinessService(db).evaluate(
        approval.id, UUID(user["sub"])
    )


@router.get("/{application_id}/query-center")
async def get_query_center(
    application_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get the entrepreneur query-resolution workspace for an application."""
    approval = await _resolve_approval(db, user, application_id)
    from app.services.query_resolution import QueryResolutionService
    return await QueryResolutionService(db).resolve_for_approval(approval)


@router.patch("/{application_id}/query-center")
async def save_query_response(
    application_id: str,
    payload: dict,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Save a draft or mark a query response ready."""
    approval = await _resolve_approval(db, user, application_id)
    if approval.status.value != "QUERY_RAISED":
        raise HTTPException(status_code=400, detail="This application has no open query to answer")
    query_id = payload.get("query_id")
    response_text = payload.get("response_text", "")
    if not query_id:
        raise HTTPException(status_code=400, detail="query_id is required")
    from app.services.query_resolution import QueryResolutionService
    try:
        record = await QueryResolutionService(db).save_response(
            approval, query_id, response_text, bool(payload.get("ready"))
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "query_id": str(record.id),
        "status": record.status,
        "response_draft": record.response_draft,
        "submitted_at": None,
    }


@router.post("/{application_id}/query-center/submit")
async def submit_query_response(
    application_id: str,
    payload: dict,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Record an applicant query response and move QUERY_RAISED back to SUBMITTED.

    No external government API is called by this endpoint.
    """
    approval = await _resolve_approval(db, user, application_id)
    if approval.status.value != "QUERY_RAISED":
        raise HTTPException(status_code=400, detail="This application does not have an open query")
    query_id = payload.get("query_id")
    if not query_id:
        raise HTTPException(status_code=400, detail="query_id is required")
    from app.services.query_resolution import QueryResolutionService
    try:
        return await QueryResolutionService(db).submit_response(
            approval, query_id, payload.get("response_text")
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{application_id}/transitions")
async def get_possible_transitions(
    application_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List the allowed next states for an application (spec §21)."""
    approval = await _resolve_approval(db, user, application_id)
    from app.services.approval_workflow import ApprovalWorkflowEngine
    role = user.get("role", "ENTREPRENEUR")
    engine = ApprovalWorkflowEngine(role)
    return {
        "application_id": approval.application_id or str(approval.id),
        "current_status": approval.status.value if hasattr(approval.status, "value") else str(approval.status),
        "available_transitions": engine.list_possible_transitions(approval.status),
    }


async def _enforce_submission_readiness(approval: Approval, user: dict, db: AsyncSession) -> dict:
    """Return readiness or raise a structured 409 for blocked entrepreneur submits."""
    if user.get("role") != "ENTREPRENEUR":
        return {"can_submit": True}

    from app.services.submission_readiness import SubmissionReadinessService

    readiness = await SubmissionReadinessService(db).evaluate(
        approval.id, UUID(user["sub"])
    )
    if not readiness["can_submit"]:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "PRE_SUBMISSION_READINESS_BLOCKED",
                "message": "Resolve the pre-submission readiness checks before submitting.",
                "readiness": readiness,
            },
        )
    return readiness


@router.post("/{application_id}/transition")
async def transition_application(
    application_id: str,
    body: dict,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Request a state-machine transition (spec §21)."""
    approval = await _resolve_approval(db, user, application_id)
    target = (body or {}).get("to_status")
    if not target:
        raise HTTPException(status_code=400, detail="Missing 'to_status'")

    from app.services.approval_workflow import ApprovalWorkflowEngine
    engine = ApprovalWorkflowEngine(user.get("role", "ENTREPRENEUR"))
    try:
        requested_status = ApprovalStatus[target.upper()]
    except (KeyError, AttributeError) as exc:
        raise HTTPException(status_code=400, detail=f"Unknown status: {target}") from exc

    if requested_status == ApprovalStatus.SUBMITTED:
        await _enforce_submission_readiness(approval, user, db)

    decision = engine.apply(approval, requested_status)
    if not decision.allowed:
        raise HTTPException(status_code=400, detail=decision.error or "Transition not allowed")

    await db.commit()
    await db.refresh(approval)

    # Raise a notification about the status change.
    try:
        result = await db.execute(select(Project).where(Project.id == approval.project_id))
        project = result.scalar_one_or_none()
        owner_id = str(project.user_id) if project else None
        if owner_id:
            from app.notifications.service import NotificationService
            await NotificationService(db).create(
                owner_id,
                "Application Status Updated",
                f"Your application for {approval.name} is now {decision.requested.value}.",
                category="approval",
                severity="info",
                project_id=approval.project_id,
                reference_id=str(approval.id),
            )
    except Exception as exc:  # noqa: BLE001 - side-channel must not break the transition
        logger.warning("Owner notification failed after decision: %s", exc)
        db.rollback()

    return {**_application_payload(approval, None), "transition": decision.to_dict()}



@router.post("/{application_id}/submit")
async def submit_application(
    application_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Transition an approval to SUBMITTED via the workflow engine (spec §21)
    and raise an in-app notification."""
    approval = await _resolve_approval(db, user, application_id)
    await _enforce_submission_readiness(approval, user, db)
    from app.services.approval_workflow import ApprovalWorkflowEngine
    engine = ApprovalWorkflowEngine(user.get("role", "ENTREPRENEUR"))
    decision = engine.apply(approval, ApprovalStatus.SUBMITTED)
    if not decision.allowed:
        raise HTTPException(status_code=400, detail=decision.error or "Cannot submit application in current state")
    await db.commit()
    await db.refresh(approval)

    # Track the application with the government integration layer (spec §19)
    # so live-status sync polls it. Uses the mock submission id by default.
    try:
        from app.integrations.government_adapters import system_for_department
        from app.services.gateway_service import GatewayService
        from app.services.gov_sync_service import GovSyncService
        system = system_for_department(approval.department) or "maitri"
        submission = await GatewayService().submit(system, {"sla_days": approval.estimated_processing_days or 30})
        submission_data = (submission or {}).get("data") if isinstance((submission or {}).get("data"), dict) else {}
        gov_app_id = (
            submission_data.get("application_id")
            or (submission or {}).get("application_id")
        )
        if gov_app_id:
            await GovSyncService(db).track(approval, system, gov_app_id)
    except Exception as e:  # noqa: BLE001 - tracking is best-effort; the application was already submitted
        logger.warning("Government tracking failed for submitted application %s: %s", approval.id, e)
        db.rollback()

    from app.models import Project
    from app.notifications.service import NotificationService
    try:
        result = await db.execute(select(Project).where(Project.id == approval.project_id))
        project = result.scalar_one_or_none()
        owner_id = str(project.user_id) if project else None
        if owner_id:
            await NotificationService(db).create(
                owner_id,
                "Application Submitted",
                f"Your application for {approval.name} has been submitted to {approval.department}.",
                category="approval",
                severity="info",
                project_id=approval.project_id,
                reference_id=str(approval.id),
            )
    except Exception as exc:  # noqa: BLE001 - side-channel must not break the submission
        logger.warning("Owner notification failed after submission: %s", exc)
        db.rollback()

    return _application_payload(approval, None)