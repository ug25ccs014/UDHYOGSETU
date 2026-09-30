"""Explore Government Services API — discover, check, prepare, apply, track.

The Explore module does not introduce a second application system: saving a
service to a checklist creates an ``Approval`` (NOT_STARTED), and everything
that follows (submit, track, SLA, officer review, audit, notifications) uses the
existing application APIs and workflow engine.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_owned_approval,
    get_owned_project,
    require_admin,
    require_auth,
)
from app.core.database import get_db_session
from app.models import Document
from app.schemas import (
    ExploreChecklistRequest,
    ExploreCheckRequest,
    ExploreDocumentAttachRequest,
    GovernmentServiceCreate,
    GovernmentServiceResponse,
)
from app.services.explore_service import ExploreService
from app.services.integration_transparency import service_integration

router = APIRouter(prefix="/explore", tags=["explore"])


async def _resolve_service(db: AsyncSession, service_id: str):
    service = await ExploreService(db).get_service(service_id)
    if not service or not service.is_active:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


@router.get("/services", response_model=list[GovernmentServiceResponse])
async def list_services(
    q: str | None = None,
    category: str | None = None,
    authority: str | None = None,
    application_mode: str | None = None,
    service_type: str | None = None,
    limit: int = 100,
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    """Search / filter the government services catalog."""
    service = ExploreService(db)
    services = await service.list_services(
        q=q, category=category, authority=authority,
        application_mode=application_mode, service_type=service_type, limit=limit,
    )
    return [_service_payload(item) for item in services]


@router.get("/services/categories")
async def list_categories(
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    return {"categories": await ExploreService(db).get_categories()}


@router.get("/services/{service_id}", response_model=GovernmentServiceResponse)
async def get_service(
    service_id: str,
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    """Service catalogue details by slug or id."""
    return _service_payload(await _resolve_service(db, service_id))


@router.get("/services/{service_id}/documents")
async def service_documents(
    service_id: str,
    project_id: UUID | None = None,
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    """Document checklist for a service. If ``project_id`` is supplied (and
    owned by the caller) each requirement is annotated with whether the project
    already holds a matching document, so the user avoids re-uploading."""
    service = await _resolve_service(db, service_id)

    required = []
    for entry in service.applicable_documents or []:
        if isinstance(entry, str):
            required.append({"document_type": entry, "description": entry, "required": True})
        else:
            required.append(
                {
                    "document_type": entry.get("document_type") or entry.get("description") or "Document",
                    "description": entry.get("description") or entry.get("document_type") or "",
                    "required": entry.get("required", True),
                }
            )

    rule = await ExploreService(db).get_rule(service)
    if rule and rule.required_documents:
        known = {r["document_type"] for r in required}
        for extra in rule.required_documents:
            if extra not in known:
                required.append({"document_type": extra, "description": extra, "required": True})
                known.add(extra)

    project_documents = []
    if project_id:
        project = await get_owned_project(project_id, user, db)
        from app.services.document_processor import DocumentProcessorService

        docs = await DocumentProcessorService(db).list_project_documents(project.id)
        for d in docs:
            doc_type = (d.custom_metadata or {}).get("document_type") or ""
            matches = [i for i, req in enumerate(required) if doc_type and req["document_type"].lower() in doc_type.lower()]
            project_documents.append(
                {
                    "id": str(d.id),
                    "file_name": d.file_name,
                    "status": d.status.value if hasattr(d.status, "value") else str(d.status),
                    "document_type": doc_type or None,
                    "matches_requirement": matches,
                }
            )

    return {
        "service_id": str(service.id),
        "service_slug": service.slug,
        "required_documents": required,
        "project_id": str(project_id) if project_id else None,
        "project_documents": project_documents,
    }


@router.post("/services/{service_id}/check-applicability")
async def check_applicability(
    service_id: str,
    body: ExploreCheckRequest,
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    """Deterministically evaluate whether a service applies to the caller's project."""
    service = await _resolve_service(db, service_id)
    project = await get_owned_project(body.project_id, user, db)
    return await ExploreService(db).check_applicability(service, project)


@router.post("/services/{service_id}/checklist")
async def add_to_checklist(
    service_id: str,
    body: ExploreChecklistRequest,
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    """Save a service to the caller's application checklist (idempotent)."""
    service = await _resolve_service(db, service_id)
    project = await get_owned_project(body.project_id, user, db)
    explore = ExploreService(db)
    approval, created = await explore.add_to_checklist(service, project.id, user["sub"])
    payload = await explore.checklist_requirements(approval)
    return {**payload, "created": created}


@router.get("/checklist/{approval_id}")
async def checklist_detail(
    approval_id: UUID,
    approval: object = Depends(get_owned_approval),
    db: AsyncSession = Depends(get_db_session),
):
    """Checklist application details: requirements, linked documents, transitions."""
    return await ExploreService(db).checklist_requirements(approval)


@router.post("/checklist/{approval_id}/start")
async def start_checklist_application(
    approval_id: UUID,
    approval: object = Depends(get_owned_approval),
    db: AsyncSession = Depends(get_db_session),
):
    """Move a checklisted application into DRAFT (NOT_STARTED -> DRAFT)."""
    return await ExploreService(db).start_application(approval)


@router.post("/checklist/{approval_id}/attach-document")
async def attach_document(
    approval_id: UUID,
    body: ExploreDocumentAttachRequest,
    approval: object = Depends(get_owned_approval),
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    """Attach an owned document to an application (fills approval_documents)."""
    result = await db.execute(select(Document).where(Document.id == body.document_id))
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    await get_owned_project(document.project_id, user, db)
    service = ExploreService(db)
    result = await service.attach_document(approval, document)
    return {**result, "requirements": (await service.checklist_requirements(approval))["required_documents"]}


@router.post("/checklist/{approval_id}/detach-document")
async def detach_document(
    approval_id: UUID,
    body: ExploreDocumentAttachRequest,
    approval: object = Depends(get_owned_approval),
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    service = ExploreService(db)
    return await service.detach_document(approval, body.document_id)


def _service_payload(service):
    """Serialize a service plus effective, truthful integration metadata."""
    return {
        "id": service.id,
        "slug": service.slug,
        "name": service.name,
        "description": service.description,
        "category": service.category,
        "authority": service.authority,
        "department": service.department,
        "service_type": service.service_type,
        "application_mode": service.application_mode,
        "status": service.status.value if hasattr(service.status, "value") else service.status,
        "official_reference": service.official_reference,
        "external_portal_url": service.external_portal_url,
        "applicable_documents": service.applicable_documents or [],
        "fees": service.fees,
        "eligibility_summary": service.eligibility_summary,
        "risk_level": service.risk_level,
        "sla_days": service.sla_days,
        "renewal_period_days": service.renewal_period_days,
        "approval_rule_id": service.approval_rule_id,
        "gateway_system": service.gateway_system,
        "is_demo": service.is_demo,
        "is_active": service.is_active,
        "integration": service_integration(service),
    }


# ---------------------------------------------------------------------------
# Admin catalog management (ADMIN only)
# ---------------------------------------------------------------------------
@router.post("/admin/services", response_model=GovernmentServiceResponse, status_code=201)
async def create_service(
    service_data: GovernmentServiceCreate,
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    provider = ExploreService(db)
    if await provider.get_service(service_data.slug):
        raise HTTPException(status_code=409, detail="A service with this slug already exists")
    from app.models import GovernmentService

    service = GovernmentService(**service_data.model_dump())
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return _service_payload(service)


@router.patch("/admin/services/{service_id}", response_model=GovernmentServiceResponse)
async def update_service(
    service_id: str,
    update_data: dict,
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Update a catalog service. Only document-editable fields are honoured."""
    service = await _resolve_service(db, service_id)

    allowed = {
        "name", "description", "category", "authority", "department", "service_type",
        "application_mode", "official_reference", "external_portal_url",
        "applicable_documents", "fees", "eligibility_summary", "risk_level",
        "sla_days", "renewal_period_days", "gateway_system", "is_demo", "is_active",
    }
    filtered = {k: v for k, v in (update_data or {}).items() if k in allowed}
    for key, value in filtered.items():
        setattr(service, key, value)

    await db.commit()
    await db.refresh(service)
    return _service_payload(service)