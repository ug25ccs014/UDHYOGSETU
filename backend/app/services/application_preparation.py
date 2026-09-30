"""Auto-prefill and applicant-side application preparation.

This service composes an application draft from the existing Business Profile and
Project models. It persists only explicit user overrides plus preparation status;
source-backed values are resolved dynamically so profile changes can propagate to
applications that have not overridden those fields.

This is a preparation aid, not an official government form engine or statutory
submission determination.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Approval, ApplicationPreparation, BusinessProfile, Document
from app.services.submission_readiness import SubmissionReadinessService


FIELD_CATALOG: tuple[dict[str, Any], ...] = (
    # Business identity
    {"key": "company_name", "label": "Company / Legal Name", "section": "Business identity", "source": "BUSINESS_PROFILE", "source_path": "company_name", "required": True, "editable": True, "kind": "text"},
    {"key": "business_type", "label": "Business Type", "section": "Business identity", "source": "BUSINESS_PROFILE", "source_path": "business_type", "required": True, "editable": True, "kind": "text"},
    {"key": "industry", "label": "Industry", "section": "Business identity", "source": "BUSINESS_PROFILE", "source_path": "industry", "required": True, "editable": True, "kind": "text"},
    {"key": "sector", "label": "Sector", "section": "Business identity", "source": "BUSINESS_PROFILE", "source_path": "sector", "required": True, "editable": True, "kind": "text"},
    {"key": "pan", "label": "PAN", "section": "Business identity", "source": "BUSINESS_PROFILE", "source_path": "pan", "required": False, "editable": True, "kind": "text"},
    {"key": "gstin", "label": "GSTIN", "section": "Business identity", "source": "BUSINESS_PROFILE", "source_path": "gstin", "required": False, "editable": True, "kind": "text"},
    {"key": "udyam_number", "label": "Udyam Number", "section": "Business identity", "source": "BUSINESS_PROFILE", "source_path": "udyam_number", "required": False, "editable": True, "kind": "text"},
    # Registered office
    {"key": "registered_address", "label": "Registered Address", "section": "Registered office", "source": "BUSINESS_PROFILE", "source_path": "registered_address", "required": False, "editable": True, "kind": "textarea"},
    {"key": "registered_state", "label": "Registered State", "section": "Registered office", "source": "BUSINESS_PROFILE", "source_path": "registered_state", "required": False, "editable": True, "kind": "text"},
    {"key": "registered_district", "label": "Registered District", "section": "Registered office", "source": "BUSINESS_PROFILE", "source_path": "registered_district", "required": False, "editable": True, "kind": "text"},
    {"key": "registered_city", "label": "Registered City", "section": "Registered office", "source": "BUSINESS_PROFILE", "source_path": "registered_city", "required": False, "editable": True, "kind": "text"},
    {"key": "registered_pincode", "label": "Registered PIN Code", "section": "Registered office", "source": "BUSINESS_PROFILE", "source_path": "registered_pincode", "required": False, "editable": True, "kind": "text"},
    # Project
    {"key": "project_name", "label": "Project Name", "section": "Project details", "source": "PROJECT", "source_path": "name", "required": True, "editable": True, "kind": "text"},
    {"key": "project_stage", "label": "Project Stage", "section": "Project details", "source": "PROJECT", "source_path": "project_stage", "required": True, "editable": True, "kind": "text"},
    {"key": "investment_amount", "label": "Investment Amount (₹)", "section": "Project details", "source": "PROJECT", "source_path": "investment_amount", "required": True, "editable": True, "kind": "number"},
    {"key": "location_state", "label": "Project State", "section": "Project details", "source": "PROJECT", "source_path": "location_state", "required": True, "editable": True, "kind": "text"},
    {"key": "location_district", "label": "Project District", "section": "Project details", "source": "PROJECT", "source_path": "location_district", "required": True, "editable": True, "kind": "text"},
    {"key": "location_city", "label": "Project City", "section": "Project details", "source": "PROJECT", "source_path": "location_city", "required": True, "editable": True, "kind": "text"},
    {"key": "location_industrial_area", "label": "Industrial Area", "section": "Project details", "source": "PROJECT", "source_path": "location_industrial_area", "required": False, "editable": True, "kind": "text"},
    {"key": "location_midc_estate", "label": "MIDC Estate", "section": "Project details", "source": "PROJECT", "source_path": "location_midc_estate", "required": False, "editable": True, "kind": "text"},
    {"key": "land_type", "label": "Land Type", "section": "Project details", "source": "PROJECT", "source_path": "land_type", "required": False, "editable": True, "kind": "text"},
    # Operations
    {"key": "employees", "label": "Employees", "section": "Operations", "source": "PROJECT", "source_path": "employees", "required": False, "editable": True, "kind": "number"},
    {"key": "production_type", "label": "Production Type", "section": "Operations", "source": "PROJECT", "source_path": "production_type", "required": False, "editable": True, "kind": "text"},
    {"key": "hazardous_materials", "label": "Hazardous Materials", "section": "Operations", "source": "PROJECT", "source_path": "hazardous_materials", "required": False, "editable": True, "kind": "boolean"},
    {"key": "has_boiler", "label": "Boiler Present", "section": "Operations", "source": "PROJECT", "source_path": "has_boiler", "required": False, "editable": True, "kind": "boolean"},
    {"key": "electricity_load", "label": "Electricity Load", "section": "Operations", "source": "PROJECT", "source_path": "electricity_load", "required": False, "editable": True, "kind": "number"},
    {"key": "water_consumption", "label": "Water Consumption", "section": "Operations", "source": "PROJECT", "source_path": "water_consumption", "required": False, "editable": True, "kind": "number"},
    {"key": "pollution_potential", "label": "Pollution Potential", "section": "Operations", "source": "PROJECT", "source_path": "pollution_potential", "required": False, "editable": True, "kind": "text"},
    {"key": "building_type", "label": "Building Type", "section": "Operations", "source": "PROJECT", "source_path": "building_type", "required": False, "editable": True, "kind": "text"},
)

_FIELD_MAP = {entry["key"]: entry for entry in FIELD_CATALOG}


def _empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


class ApplicationPreparationService:
    """Build and persist applicant-side preparation data for an Approval."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, approval_id: UUID | str, user_id: UUID) -> dict:
        approval = await self._get_owned_application(approval_id, user_id)
        preparation = await self._get_or_create_preparation(approval, persist=False)
        return await self._build_payload(approval, preparation)

    async def save(
        self,
        approval_id: UUID | str,
        user_id: UUID,
        overrides: dict[str, Any] | None = None,
        reset_fields: list[str] | None = None,
        document_ids: list[UUID] | None = None,
        mark_prepared: bool = False,
    ) -> dict:
        approval = await self._get_owned_application(approval_id, user_id)
        status_value = approval.status.value if hasattr(approval.status, "value") else str(approval.status)
        if status_value not in {"NOT_STARTED", "DRAFT"}:
            raise ValueError("Application preparation can only be edited before submission")
        preparation = await self._get_or_create_preparation(approval, persist=True)

        clean_overrides = dict(preparation.overrides or {})
        for key in reset_fields or []:
            self._validate_field_key(key)
            clean_overrides.pop(key, None)

        for key, value in (overrides or {}).items():
            self._validate_field_key(key)
            entry = _FIELD_MAP[key]
            if not entry["editable"]:
                raise ValueError(f"Field '{key}' is not editable")
            clean_overrides[key] = self._normalize_value(entry["kind"], value)

        preparation.overrides = clean_overrides
        preparation.updated_at = datetime.utcnow()

        if document_ids:
            await self._attach_owned_documents(approval, document_ids)

        # Any edit invalidates a previous prepared snapshot; the applicant must
        # review the updated values again.
        if not mark_prepared and preparation.status in {"PREPARED", "STALE"}:
            preparation.status = "DRAFT"
            preparation.prepared_at = None
            preparation.prepared_snapshot = None
            preparation.prepared_source_snapshot = None

        payload = await self._build_payload(approval, preparation)
        required_missing = payload["summary"]["missing_required_fields"]
        if mark_prepared and required_missing:
            raise ValueError(
                "Application preparation is incomplete. Missing required fields: "
                + ", ".join(required_missing)
            )

        if mark_prepared:
            snapshot = {field["key"]: field["value"] for field in payload["fields"]}
            source_snapshot = {field["key"]: field.get("source_value") for field in payload["fields"]}
            preparation.status = "PREPARED"
            preparation.prepared_at = datetime.utcnow()
            preparation.prepared_snapshot = snapshot
            preparation.prepared_source_snapshot = source_snapshot

        await self.db.commit()
        await self.db.refresh(preparation)
        return await self._build_payload(approval, preparation)

    async def _get_owned_application(self, application_id: UUID | str, user_id: UUID) -> Approval:
        result = await self.db.execute(
            select(Approval)
            .options(selectinload(Approval.project), selectinload(Approval.documents))
            .where(Approval.application_id == str(application_id))
        )
        approval = result.scalar_one_or_none()
        if not approval:
            try:
                result = await self.db.execute(
                    select(Approval)
                    .options(selectinload(Approval.project), selectinload(Approval.documents))
                    .where(Approval.id == UUID(str(application_id)))
                )
                approval = result.scalar_one_or_none()
            except (ValueError, AttributeError, TypeError):
                approval = None
        if not approval or not approval.project or str(approval.project.user_id) != str(user_id):
            raise ValueError("Application not found or not owned by the current user")
        return approval

    async def _get_or_create_preparation(self, approval: Approval, persist: bool) -> ApplicationPreparation:
        if "preparation" in approval.__dict__ and approval.preparation:
            return approval.preparation
        result = await self.db.execute(
            select(ApplicationPreparation).where(ApplicationPreparation.approval_id == approval.id)
        )
        preparation = result.scalar_one_or_none()
        if preparation:
            return preparation
        preparation = ApplicationPreparation(approval_id=approval.id, overrides={}, status="DRAFT")
        if persist:
            self.db.add(preparation)
            await self.db.flush()
        return preparation

    async def _build_payload(self, approval: Approval, preparation: ApplicationPreparation) -> dict:
        profile = (
            await self.db.execute(
                select(BusinessProfile).where(BusinessProfile.user_id == approval.project.user_id)
            )
        ).scalar_one_or_none()

        base_values = self._source_values(profile, approval.project)
        overrides = dict(preparation.overrides or {})
        stored_snapshot = dict(preparation.prepared_snapshot or {})
        effective_status = preparation.status
        stale_fields: list[str] = []
        stale_keys: set[str] = set()
        if preparation.status == "PREPARED" and stored_snapshot:
            stored_sources = dict(preparation.prepared_source_snapshot or {})
            for key, label in ((entry["key"], entry["label"]) for entry in FIELD_CATALOG):
                if key not in overrides and stored_sources.get(key) != base_values.get(key):
                    stale_fields.append(label)
                    stale_keys.add(key)
            if stale_fields:
                effective_status = "STALE"

        readiness = await SubmissionReadinessService(self.db).evaluate(approval.id, approval.project.user_id)
        document_requirements = [
            item.get("requirement", "")
            for item in readiness.get("document_checklist", [])
            if item.get("required")
        ]
        required_keys = self._required_keys(document_requirements)

        fields = []
        for entry in FIELD_CATALOG:
            key = entry["key"]
            source_value = base_values.get(key)
            if effective_status in {"PREPARED", "STALE"} and key in stored_snapshot:
                value = stored_snapshot[key]
            else:
                value = overrides[key] if key in overrides else source_value
            required = key in required_keys
            filled = not _empty(value)
            effective_source = (
                "USER_OVERRIDE"
                if key in overrides
                else "PREPARED_SNAPSHOT"
                if effective_status == "STALE" and key in stored_snapshot
                else entry["source"]
            )
            fields.append(
                {
                    **entry,
                    "required": required,
                    "value": value,
                    "source_value": source_value,
                    "status": "FILLED" if filled else "MISSING" if required else "OPTIONAL_EMPTY",
                    "effective_source": effective_source,
                    "source_label": self._source_label(effective_source),
                    "has_override": key in overrides,
                    "source_changed": key in stale_keys,
                }
            )

        recommended = self._recommended_documents(readiness)
        attached = [
            {
                "id": str(doc.id),
                "file_name": doc.file_name,
                "status": doc.status.value if hasattr(doc.status, "value") else str(doc.status),
                "document_type": (doc.custom_metadata or {}).get("document_type"),
            }
            for doc in approval.documents
        ]

        filled_required = sum(1 for f in fields if f["required"] and f["status"] == "FILLED")
        total_required = sum(1 for f in fields if f["required"])
        missing_required = [f["label"] for f in fields if f["required"] and f["status"] != "FILLED"]

        return {
            "application_id": approval.application_id or str(approval.id),
            "approval_id": str(approval.id),
            "approval_name": approval.name,
            "department": approval.department,
            "project_id": str(approval.project_id),
            "project_name": approval.project.name,
            "application_status": approval.status.value if hasattr(approval.status, "value") else str(approval.status),
            "status": effective_status,
            "prepared_at": preparation.prepared_at.isoformat() if preparation.prepared_at else None,
            "stale_fields": stale_fields,
            "summary": {
                "filled_required_fields": filled_required,
                "required_fields": total_required,
                "missing_required_fields": missing_required,
                "filled_fields": sum(1 for f in fields if f["status"] == "FILLED"),
                "total_fields": len(fields),
                "preparation_score": round((filled_required / total_required) * 100) if total_required else 100,
                "readiness_score": readiness["score"],
                "readiness_state": readiness["readiness_state"],
            },
            "fields": fields,
            "attached_documents": attached,
            "recommended_documents": recommended,
            "sources": {
                "business_profile": "stored user profile",
                "project": "stored project profile",
                "government_api": "not_connected",
            },
            "disclaimer": "Prepared application data is an applicant-side draft and is not an official government form or statutory determination.",
        }

    def _source_values(self, profile: BusinessProfile | None, project) -> dict[str, Any]:
        def choose(profile_key: str, project_key: str) -> Any:
            profile_value = getattr(profile, profile_key, None) if profile else None
            return profile_value if not _empty(profile_value) else getattr(project, project_key, None)

        return {
            "company_name": choose("company_name", "company_name"),
            "business_type": choose("business_type", "business_type"),
            "industry": choose("industry", "industry"),
            "sector": choose("sector", "sector"),
            "pan": getattr(profile, "pan", None) if profile else None,
            "gstin": getattr(profile, "gstin", None) if profile else None,
            "udyam_number": getattr(profile, "udyam_number", None) if profile else None,
            "registered_address": getattr(profile, "registered_address", None) if profile else None,
            "registered_state": getattr(profile, "registered_state", None) if profile else None,
            "registered_district": getattr(profile, "registered_district", None) if profile else None,
            "registered_city": getattr(profile, "registered_city", None) if profile else None,
            "registered_pincode": getattr(profile, "registered_pincode", None) if profile else None,
            "project_name": getattr(project, "name", None),
            "project_stage": getattr(project, "project_stage", None),
            "investment_amount": getattr(project, "investment_amount", None),
            "location_state": getattr(project, "location_state", None),
            "location_district": getattr(project, "location_district", None),
            "location_city": getattr(project, "location_city", None),
            "location_industrial_area": getattr(project, "location_industrial_area", None),
            "location_midc_estate": getattr(project, "location_midc_estate", None),
            "land_type": getattr(project, "land_type", None),
            "employees": getattr(project, "employees", None),
            "production_type": getattr(project, "production_type", None),
            "hazardous_materials": getattr(project, "hazardous_materials", None),
            "has_boiler": getattr(project, "has_boiler", None),
            "electricity_load": getattr(project, "electricity_load", None),
            "water_consumption": getattr(project, "water_consumption", None),
            "pollution_potential": getattr(project, "pollution_potential", None),
            "building_type": getattr(project, "building_type", None),
        }

    def _required_keys(self, document_labels: list[str]) -> set[str]:
        keys = {
            "company_name", "business_type", "industry", "sector",
            "project_name", "project_stage", "investment_amount",
            "location_state", "location_district", "location_city",
        }
        normalized = {label.lower() for label in document_labels}
        if any("pan card" in label or label.strip() == "pan" for label in normalized):
            keys.add("pan")
        if any("business address proof" in label or "registered address" in label for label in normalized):
            keys.add("registered_address")
        return keys

    async def _attach_owned_documents(self, approval: Approval, document_ids: list[UUID]) -> None:
        if not document_ids:
            return
        result = await self.db.execute(select(Document).where(Document.id.in_(document_ids)))
        documents = list(result.scalars().all())
        if len(documents) != len(set(document_ids)):
            raise ValueError("One or more selected documents could not be found")
        for document in documents:
            if str(document.project_id) != str(approval.project_id):
                raise ValueError("Selected document does not belong to the application project")
            if not any(str(existing.id) == str(document.id) for existing in approval.documents):
                approval.documents.append(document)

    def _recommended_documents(self, readiness: dict) -> list[dict]:
        suggestions: dict[str, dict] = {}
        for item in readiness.get("document_checklist", []):
            for candidate in item.get("candidate_documents", []) or []:
                key = candidate["document_id"]
                existing = suggestions.get(key)
                row = {
                    "document_id": key,
                    "file_name": candidate.get("file_name"),
                    "status": candidate.get("status"),
                    "document_type": candidate.get("document_type"),
                    "match_score": candidate.get("match_score", 0),
                    "requirements": [item.get("requirement")],
                }
                if existing:
                    existing["requirements"].append(item.get("requirement"))
                else:
                    suggestions[key] = row
        return sorted(suggestions.values(), key=lambda x: (-x.get("match_score", 0), x.get("file_name") or ""))

    @staticmethod
    def _source_label(source: str) -> str:
        return {
            "BUSINESS_PROFILE": "Business Profile",
            "PROJECT": "Project Profile",
            "USER_OVERRIDE": "Applicant edited",
            "PREPARED_SNAPSHOT": "Prepared snapshot",
        }.get(source, source)

    @staticmethod
    def _validate_field_key(key: str) -> None:
        if key not in _FIELD_MAP:
            raise ValueError(f"Unknown application preparation field: {key}")

    @staticmethod
    def _normalize_value(kind: str, value: Any) -> Any:
        if value is None:
            return None
        if kind in {"text", "textarea"}:
            return str(value).strip()
        if kind == "number":
            if value == "":
                return None
            try:
                number = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError("Numeric preparation fields must contain a valid number") from exc
            return int(number) if number.is_integer() else number
        if kind == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                lowered = value.lower().strip()
                if lowered in {"true", "1", "yes"}:
                    return True
                if lowered in {"false", "0", "no"}:
                    return False
            raise ValueError("Boolean preparation fields must contain true or false")
        return value
