"""Business Profile + reusable document vault service.

Step 2 introduces an entrepreneur-owned business identity record that can be
reused across projects. Existing project-scoped Documents remain the canonical
file records; ``business_profile_documents`` simply marks which of those files
the user has promoted into their reusable vault.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.mock_gov_api import get_mock_gov_api
from app.models import (
    BusinessProfile,
    Document,
    Project,
    business_profile_documents,
)
from app.services.document_intelligence import GSTIN_RE, PAN_RE


PROFILE_REQUIRED_FIELDS = {
    "company_name": "Company name",
    "business_type": "Business type",
    "industry": "Industry",
    "sector": "Sector",
    "registered_address": "Registered address",
    "registered_state": "Registered state",
    "registered_city": "Registered city",
}

IDENTITY_FIELDS = ("pan", "gstin", "udyam_number")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class BusinessProfileService:
    """Owns business-profile CRUD, verification state and document-vault access."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, user_id: UUID) -> BusinessProfile:
        result = await self.db.execute(
            select(BusinessProfile).where(BusinessProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if profile:
            return profile

        profile = BusinessProfile(user_id=user_id)
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def update(self, user_id: UUID, payload: dict) -> BusinessProfile:
        profile = await self.get_or_create(user_id)
        verification = dict(profile.verification_status or {})

        for key, value in payload.items():
            if not hasattr(profile, key):
                continue

            if isinstance(value, str):
                value = value.strip()

            if key in {"pan", "gstin"} and value:
                value = value.upper()

            old_value = getattr(profile, key)
            setattr(profile, key, value)

            if key in IDENTITY_FIELDS and old_value != value:
                verification[key] = self._verification_state_for_value(key, value)

        profile.verification_status = verification
        profile.updated_at = _now()
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def verify_identity(self, user_id: UUID) -> BusinessProfile:
        """Run prototype verification against the existing deterministic mock layer.

        This is deliberately NOT presented as official government verification.
        """
        profile = await self.get_or_create(user_id)
        mock = get_mock_gov_api()

        verification = dict(profile.verification_status or {})
        details = dict(profile.verification_details or {})

        checks = (
            ("pan", profile.pan, mock.verify_pan),
            ("gstin", profile.gstin, mock.verify_gstin),
            ("udyam_number", profile.udyam_number, mock.verify_udyam),
        )

        for key, value, verifier in checks:
            if not value:
                verification[key] = {
                    "status": "NOT_PROVIDED",
                    "source": "Prototype Verification",
                    "verified_at": None,
                }
                details[key] = None
                continue

            if self._identity_format_is_invalid(key, value):
                verification[key] = {
                    "status": "FORMAT_INVALID",
                    "source": "Local format validation",
                    "verified_at": None,
                }
                details[key] = {"valid": False}
                continue

            response = await verifier(value)
            data = (response or {}).get("data") or {}
            valid = bool(data.get("valid"))
            verification[key] = {
                "status": "PROTOTYPE_VERIFIED" if valid else "PROTOTYPE_REJECTED",
                "source": "Prototype Verification",
                "verified_at": _now().isoformat(),
            }
            details[key] = {
                "valid": valid,
                "status": data.get("status"),
            }

        profile.verification_status = verification
        profile.verification_details = details
        profile.updated_at = _now()
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def list_vault_documents(self, user_id: UUID) -> list[dict]:
        """Return every user-owned project document with vault membership."""
        result = await self.db.execute(
            select(Document, Project)
            .join(Project, Project.id == Document.project_id)
            .where(Project.user_id == user_id)
            .order_by(Document.created_at.desc())
        )
        rows = result.all()

        profile = await self.get_or_create(user_id)
        vault_result = await self.db.execute(
            select(business_profile_documents.c.document_id).where(
                business_profile_documents.c.business_profile_id == profile.id
            )
        )
        vault_ids = {str(row[0]) for row in vault_result.all()}

        return [
            self._document_payload(
                document=document,
                project=project,
                in_vault=str(document.id) in vault_ids,
            )
            for document, project in rows
        ]

    async def add_document_to_vault(self, user_id: UUID, document_id: UUID) -> dict:
        profile = await self.get_or_create(user_id)
        document, project = await self._owned_document(user_id, document_id)

        existing = await self.db.execute(
            select(business_profile_documents.c.document_id).where(
                business_profile_documents.c.business_profile_id == profile.id,
                business_profile_documents.c.document_id == document.id,
            )
        )
        if existing.first() is None:
            await self.db.execute(
                insert(business_profile_documents).values(
                    business_profile_id=profile.id,
                    document_id=document.id,
                    added_at=_now(),
                )
            )
            await self.db.commit()

        return self._document_payload(document, project, in_vault=True)

    async def remove_document_from_vault(self, user_id: UUID, document_id: UUID) -> None:
        profile = await self.get_or_create(user_id)
        # The ownership lookup intentionally happens before deleting so a user
        # cannot probe/remove a document they do not own.
        await self._owned_document(user_id, document_id)
        await self.db.execute(
            delete(business_profile_documents).where(
                business_profile_documents.c.business_profile_id == profile.id,
                business_profile_documents.c.document_id == document_id,
            )
        )
        await self.db.commit()

    def to_response(self, profile: BusinessProfile) -> dict:
        completeness = self._completeness(profile)
        verification = self._normalized_verification(profile)
        return {
            "id": profile.id,
            "user_id": profile.user_id,
            "company_name": profile.company_name,
            "business_type": profile.business_type,
            "industry": profile.industry,
            "sector": profile.sector,
            "pan": profile.pan,
            "gstin": profile.gstin,
            "udyam_number": profile.udyam_number,
            "registered_address": profile.registered_address,
            "registered_state": profile.registered_state,
            "registered_district": profile.registered_district,
            "registered_city": profile.registered_city,
            "registered_pincode": profile.registered_pincode,
            "verification_status": verification,
            "verification_details": profile.verification_details or {},
            "completeness": completeness,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
        }

    @staticmethod
    def _completeness(profile: BusinessProfile) -> dict:
        total = len(PROFILE_REQUIRED_FIELDS)
        missing = [
            label
            for field, label in PROFILE_REQUIRED_FIELDS.items()
            if not (getattr(profile, field, None) or "").strip()
        ]
        completed = total - len(missing)
        identity_present = sum(1 for field in IDENTITY_FIELDS if getattr(profile, field, None))
        return {
            "score": round((completed / total) * 100) if total else 100,
            "completed_fields": completed,
            "total_fields": total,
            "missing_fields": missing,
            "identity_fields_present": identity_present,
            "identity_fields_total": len(IDENTITY_FIELDS),
        }

    @staticmethod
    def _normalized_verification(profile: BusinessProfile) -> dict:
        raw = dict(profile.verification_status or {})
        result = {}
        for field in IDENTITY_FIELDS:
            result[field] = raw.get(
                field,
                BusinessProfileService._verification_state_for_value(field, getattr(profile, field, None)),
            )
        return result

    @staticmethod
    def _identity_format_is_invalid(field: str, value: str) -> bool:
        if field == "pan":
            return PAN_RE.fullmatch(value) is None
        if field == "gstin":
            return GSTIN_RE.fullmatch(value) is None
        return not bool(value.strip())

    @classmethod
    def _verification_state_for_value(cls, field: str, value: str | None) -> dict:
        if not value:
            status = "NOT_PROVIDED"
        elif cls._identity_format_is_invalid(field, value):
            status = "FORMAT_INVALID"
        else:
            status = "FORMAT_VALIDATED"
        return {
            "status": status,
            "source": "Local presence check" if field == "udyam_number" else "Local format validation",
            "verified_at": None,
        }

    async def _owned_document(self, user_id: UUID, document_id: UUID) -> tuple[Document, Project]:
        result = await self.db.execute(
            select(Document, Project)
            .join(Project, Project.id == Document.project_id)
            .where(
                Document.id == document_id,
                Project.user_id == user_id,
            )
        )
        row = result.first()
        if not row:
            raise ValueError("Document not found")
        return row

    @staticmethod
    def _document_payload(document: Document, project: Project, in_vault: bool) -> dict:
        custom_metadata = document.custom_metadata or {}
        return {
            "id": str(document.id),
            "file_name": document.file_name,
            "file_type": document.file_type,
            "status": document.status.value if hasattr(document.status, "value") else str(document.status),
            "document_type": custom_metadata.get("document_type")
            or (document.extracted_fields or {}).get("document_type"),
            "extracted_fields": document.extracted_fields or {},
            "validation_errors": document.validation_errors or [],
            "project_id": str(project.id),
            "project_name": project.name,
            "in_vault": in_vault,
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "updated_at": document.updated_at.isoformat() if document.updated_at else None,
        }
