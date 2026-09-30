"""Entrepreneur Business Profile and reusable Data Vault API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_auth
from app.core.database import get_db_session
from app.schemas import BusinessProfileResponse, BusinessProfileUpdate
from app.services.business_profile import BusinessProfileService

router = APIRouter(prefix="/profile", tags=["business-profile"])


@router.get("", response_model=BusinessProfileResponse)
async def get_business_profile(
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    service = BusinessProfileService(db)
    profile = await service.get_or_create(UUID(user["sub"]))
    return service.to_response(profile)


@router.patch("", response_model=BusinessProfileResponse)
async def update_business_profile(
    payload: BusinessProfileUpdate,
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    service = BusinessProfileService(db)
    profile = await service.update(
        UUID(user["sub"]),
        payload.model_dump(exclude_unset=True),
    )
    return service.to_response(profile)


@router.post("/verify", response_model=BusinessProfileResponse)
async def verify_business_identity(
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    """Run deterministic prototype identity verification.

    No live government API is contacted. The response is explicitly labelled
    ``Prototype Verification`` in the stored verification status.
    """
    service = BusinessProfileService(db)
    profile = await service.verify_identity(UUID(user["sub"]))
    return service.to_response(profile)


@router.get("/documents")
async def list_business_profile_documents(
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    service = BusinessProfileService(db)
    documents = await service.list_vault_documents(UUID(user["sub"]))
    in_vault = sum(1 for document in documents if document["in_vault"])
    return {
        "documents": documents,
        "summary": {
            "total": len(documents),
            "in_vault": in_vault,
            "available_to_add": len(documents) - in_vault,
        },
    }


@router.post("/documents/{document_id}")
async def add_document_to_vault(
    document_id: UUID,
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    service = BusinessProfileService(db)
    try:
        return await service.add_document_to_vault(UUID(user["sub"]), document_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_document_from_vault(
    document_id: UUID,
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    service = BusinessProfileService(db)
    try:
        await service.remove_document_from_vault(UUID(user["sub"]), document_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
