"""Compliance and renewal lifecycle orchestration.

This service builds on the existing ComplianceItem/Approval/Document models. It
adds deterministic operational scheduling, completion actions, and a separate
renewal-case record so the original approval remains an immutable source record.
All schedules are configured prototype/operational targets, not government
statutory guarantees.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Approval,
    ApprovalRule,
    ApprovalStatus,
    ComplianceItem,
    ComplianceStatus,
    Document,
    Project,
    RenewalCase,
    RenewalCaseStatus,
    renewal_case_documents,
)
from app.notifications.service import NotificationService
from app.services.compliance_tracker import ComplianceTracker, _naive_utc


_FREQUENCY_DAYS = {
    "monthly": 30,
    "quarterly": 90,
    "biannual": 182,
    "annual": 365,
}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _status(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


class ComplianceLifecycleService:
    """Own project-scoped compliance tasks and renewal preparation."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.tracker = ComplianceTracker(db)

    async def dashboard(self, project_id: UUID, user_id: UUID) -> dict:
        await self._ensure_owner(project_id, user_id)
        await self._materialize_and_refresh(project_id, user_id)

        items = list((await self.db.execute(
            select(ComplianceItem)
            .where(ComplianceItem.project_id == project_id)
            .order_by(ComplianceItem.next_due.asc().nullslast(), ComplianceItem.category, ComplianceItem.requirement)
        )).scalars().all())

        renewals = await self.list_renewals(project_id, user_id)
        await self._notify_renewals(project_id, user_id, renewals)
        now = _now()
        counts = {"ON_TRACK": 0, "AT_RISK": 0, "OVERDUE": 0}
        for item in items:
            counts[_status(item.status)] = counts.get(_status(item.status), 0) + 1

        categories: dict[str, dict[str, int]] = {}
        for item in items:
            bucket = categories.setdefault(item.category, {"total": 0, "compliant": 0})
            bucket["total"] += 1
            if _status(item.status) == ComplianceStatus.ON_TRACK.value:
                bucket["compliant"] += 1

        return {
            "project_id": str(project_id),
            "score": round((counts["ON_TRACK"] / len(items)) * 100, 2) if items else 0,
            "overall_score": round((counts["ON_TRACK"] / len(items)) * 100, 2) if items else 0,
            "categories": categories,
            "summary": {
                "total": len(items),
                "on_track": counts["ON_TRACK"],
                "at_risk": counts["AT_RISK"],
                "overdue": counts["OVERDUE"],
                "renewals_due": sum(1 for r in renewals if r["lifecycle_status"] in {"DUE_SOON", "OVERDUE", "IN_PROGRESS"}),
            },
            "items": [self._item_payload(i, now) for i in items],
            "renewals": renewals,
            "generated_at": now.isoformat(),
            "disclaimer": "Compliance/renewal schedules shown here are configured operational guidance and not government guarantees.",
        }

    async def complete_item(self, item_id: UUID, user_id: UUID, completed_at: datetime | None = None) -> dict:
        result = await self.db.execute(select(ComplianceItem).where(ComplianceItem.id == item_id))
        item = result.scalar_one_or_none()
        if not item:
            raise ValueError("Compliance item not found")
        await self._ensure_owner(item.project_id, user_id)
        when = _naive_utc(completed_at or _now())
        now = _now()
        if when > now + timedelta(minutes=5):
            raise ValueError("completed_at cannot be in the future")
        interval = _FREQUENCY_DAYS.get((item.frequency or "").lower())
        item.last_completed = when
        if interval:
            item.next_due = when + timedelta(days=interval)
            item.due_date = item.next_due
        item.status = ComplianceStatus.ON_TRACK
        await self.db.commit()
        from app.audit.logging import log_audit
        await log_audit(
            self.db,
            user_id=str(user_id),
            action="compliance.item.completed",
            resource_type="compliance_item",
            resource_id=str(item.id),
            details={"requirement": item.requirement, "next_due": item.next_due.isoformat() if item.next_due else None},
        )
        await NotificationService(self.db).create_once(
            user_id=user_id,
            title="Compliance task completed",
            message=f"{item.requirement} was marked complete. Next due date: {item.next_due.date().isoformat() if item.next_due else 'not configured'}.",
            category="compliance",
            severity="success",
            project_id=item.project_id,
            reference_id=str(item.id),
            window_minutes=10,
        )
        return self._item_payload(item, _now())

    async def list_renewals(self, project_id: UUID, user_id: UUID) -> list[dict]:
        await self._ensure_owner(project_id, user_id)
        approvals = list((await self.db.execute(
            select(Approval).where(
                Approval.project_id == project_id,
                Approval.status == ApprovalStatus.APPROVED,
                Approval.renewal_period_days.is_not(None),
            ).order_by(Approval.approved_at.asc().nullslast(), Approval.name)
        )).scalars().all())
        existing = list((await self.db.execute(
            select(RenewalCase).where(RenewalCase.project_id == project_id)
        )).scalars().all())
        existing_by_approval = {str(r.source_approval_id): r for r in existing}
        now = _now()
        results: list[dict] = []
        for approval in approvals:
            if not approval.approved_at:
                continue
            renewal_date = _naive_utc(approval.approved_at) + timedelta(days=approval.renewal_period_days or 365)
            advance = 90
            name = (approval.name or "").lower()
            if "mpcb" in name or "pollution" in name:
                advance = 120
            elif "boiler" in name:
                advance = 90
            elif "labour" in name:
                advance = 45
            days = (renewal_date - now).days
            case = existing_by_approval.get(str(approval.id))
            lifecycle = _status(case.status) if case else ("OVERDUE" if days < 0 else "DUE_SOON" if days <= advance else "NOT_DUE")
            results.append({
                "approval_id": str(approval.id),
                "approval_name": approval.name,
                "department": approval.department,
                "renewal_date": renewal_date.isoformat(),
                "days_until_renewal": days,
                "advance_notice_days": advance,
                "lifecycle_status": lifecycle,
                "case_id": str(case.id) if case else None,
                "case_status": _status(case.status) if case else None,
                "prepared_at": case.prepared_at.isoformat() if case and case.prepared_at else None,
                "submitted_at": case.submitted_at.isoformat() if case and case.submitted_at else None,
                "renewed_at": case.renewed_at.isoformat() if case and case.renewed_at else None,
                "external_reference": case.external_reference if case else None,
                "can_prepare": case is None or _status(case.status) in {RenewalCaseStatus.DRAFT.value, RenewalCaseStatus.PREPARING.value},
                "source": "Configured approval renewal period",
            })
        return results

    async def prepare_renewal(self, project_id: UUID, approval_id: UUID, user_id: UUID) -> dict:
        await self._ensure_owner(project_id, user_id)
        approval = (await self.db.execute(select(Approval).where(
            Approval.id == approval_id, Approval.project_id == project_id
        ))).scalar_one_or_none()
        if not approval:
            raise ValueError("Approval not found")
        if _status(approval.status) != ApprovalStatus.APPROVED.value:
            raise ValueError("Only approved approvals can enter renewal preparation")
        if not approval.renewal_period_days:
            raise ValueError("This approval has no configured renewal period")

        existing = (await self.db.execute(select(RenewalCase).where(
            RenewalCase.source_approval_id == approval_id
        ))).scalar_one_or_none()
        if existing:
            return await self.renewal_detail(existing.id, user_id)

        case = RenewalCase(
            project_id=project_id,
            source_approval_id=approval_id,
            status=RenewalCaseStatus.PREPARING.value,
            prepared_at=_now(),
            notes="Renewal preparation created in UDYOGSETU; government submission remains external until an authorized integration is available.",
        )
        self.db.add(case)
        await self.db.flush()

        # Seed the renewal package from documents attached to the original approval.
        from app.models import approval_documents
        original_doc_ids = [row[0] for row in (await self.db.execute(
            select(approval_documents.c.document_id).where(approval_documents.c.approval_id == approval_id)
        )).all()]
        for doc_id in original_doc_ids:
            await self.db.execute(insert(renewal_case_documents).values(renewal_case_id=case.id, document_id=doc_id))

        await self.db.commit()
        from app.audit.logging import log_audit
        await log_audit(
            self.db,
            user_id=str(user_id),
            action="compliance.renewal.prepared",
            resource_type="renewal_case",
            resource_id=str(case.id),
            details={"approval_id": str(approval.id), "status": case.status},
        )
        await self._notify_renewal(user_id, case, approval, "prepared")
        return await self.renewal_detail(case.id, user_id)

    async def update_renewal(
        self,
        renewal_id: UUID,
        user_id: UUID,
        status: str | None = None,
        external_reference: str | None = None,
        notes: str | None = None,
        document_ids: list[UUID] | None = None,
    ) -> dict:
        case = await self._get_owned_renewal(renewal_id, user_id)
        current = _status(case.status)
        allowed = {
            RenewalCaseStatus.DRAFT.value: {RenewalCaseStatus.PREPARING.value, RenewalCaseStatus.CANCELLED.value},
            RenewalCaseStatus.PREPARING.value: {RenewalCaseStatus.READY_FOR_SUBMISSION.value, RenewalCaseStatus.CANCELLED.value},
            RenewalCaseStatus.READY_FOR_SUBMISSION.value: {RenewalCaseStatus.SUBMITTED_EXTERNALLY.value, RenewalCaseStatus.CANCELLED.value},
            RenewalCaseStatus.SUBMITTED_EXTERNALLY.value: {RenewalCaseStatus.RENEWED.value},
            RenewalCaseStatus.RENEWED.value: set(),
            RenewalCaseStatus.CANCELLED.value: {RenewalCaseStatus.DRAFT.value},
        }
        target = status.upper() if status else None
        if target and target != current and target not in allowed.get(current, set()):
            raise ValueError(f"Renewal transition {current} -> {target} is not allowed")
        if target:
            case.status = target
            if target == RenewalCaseStatus.SUBMITTED_EXTERNALLY.value:
                case.submitted_at = _now()
            elif target == RenewalCaseStatus.RENEWED.value:
                case.renewed_at = _now()
                case.submitted_at = case.submitted_at or _now()
        if external_reference is not None:
            case.external_reference = external_reference.strip() or None
        if notes is not None:
            case.notes = notes.strip() or None

        if document_ids is not None:
            unique = list(dict.fromkeys(document_ids))
            if unique:
                owned = list((await self.db.execute(
                    select(Document.id).join(Project, Project.id == Document.project_id).where(
                        Document.id.in_(unique), Project.user_id == user_id, Document.project_id == case.project_id
                    )
                )).scalars().all())
                if len(owned) != len(unique):
                    raise ValueError("One or more renewal documents are not available to this project")
            await self.db.execute(delete(renewal_case_documents).where(renewal_case_documents.c.renewal_case_id == case.id))
            for doc_id in unique:
                await self.db.execute(insert(renewal_case_documents).values(renewal_case_id=case.id, document_id=doc_id))

        await self.db.commit()
        approval = (await self.db.execute(select(Approval).where(Approval.id == case.source_approval_id))).scalar_one()
        if target:
            from app.audit.logging import log_audit
            await log_audit(
                self.db,
                user_id=str(user_id),
                action="compliance.renewal.status_changed",
                resource_type="renewal_case",
                resource_id=str(case.id),
                details={"approval_id": str(approval.id), "to_status": target},
            )
        if target in {RenewalCaseStatus.SUBMITTED_EXTERNALLY.value, RenewalCaseStatus.RENEWED.value}:
            await self._notify_renewal(user_id, case, approval, target.lower())
        return await self.renewal_detail(renewal_id, user_id)

    async def renewal_detail(self, renewal_id: UUID, user_id: UUID) -> dict:
        case = await self._get_owned_renewal(renewal_id, user_id)
        approval = (await self.db.execute(select(Approval).where(Approval.id == case.source_approval_id))).scalar_one()
        docs = list((await self.db.execute(
            select(Document).join(
                renewal_case_documents,
                renewal_case_documents.c.document_id == Document.id,
            ).where(renewal_case_documents.c.renewal_case_id == renewal_id)
        )).scalars().all())
        rule = (await self.db.execute(select(ApprovalRule).where(ApprovalRule.name == approval.name))).scalar_one_or_none()
        required = list(rule.required_documents or []) if rule else []
        available = [self._doc_type(d) for d in docs]
        missing = [str(r.get("document_type") or r) for r in required if str(r.get("document_type") or r) not in available]
        ready = not missing
        return {
            "id": str(case.id),
            "project_id": str(case.project_id),
            "approval_id": str(approval.id),
            "approval_name": approval.name,
            "department": approval.department,
            "status": _status(case.status),
            "external_reference": case.external_reference,
            "prepared_at": case.prepared_at.isoformat() if case.prepared_at else None,
            "submitted_at": case.submitted_at.isoformat() if case.submitted_at else None,
            "renewed_at": case.renewed_at.isoformat() if case.renewed_at else None,
            "notes": case.notes,
            "documents": [self._doc_payload(d) for d in docs],
            "document_readiness": {
                "required_count": len(required),
                "available_count": len(available),
                "missing": missing,
                "ready": ready,
            },
            "can_mark_ready": _status(case.status) == RenewalCaseStatus.PREPARING.value and ready,
            "can_mark_submitted_externally": _status(case.status) == RenewalCaseStatus.READY_FOR_SUBMISSION.value,
            "can_mark_renewed": _status(case.status) == RenewalCaseStatus.SUBMITTED_EXTERNALLY.value,
            "transparency": "No government renewal submission is performed by this prototype; SUBMITTED_EXTERNALLY records an applicant-reported external submission.",
        }

    async def _materialize_and_refresh(self, project_id: UUID, user_id: UUID) -> None:
        await __import__("app.services.compliance", fromlist=["ComplianceService"]).ComplianceService(self.db).get_compliance_items(project_id)
        result = await self.db.execute(select(ComplianceItem).where(ComplianceItem.project_id == project_id))
        items = list(result.scalars().all())
        changed = False
        now = _now()
        for item in items:
            if not item.frequency:
                frequency = self._frequency_for_requirement(item.requirement)
                item.frequency = frequency
                if item.last_completed:
                    item.next_due = _naive_utc(item.last_completed) + timedelta(days=_FREQUENCY_DAYS[frequency])
                    item.due_date = item.next_due
                elif item.next_due:
                    # Existing rows from older versions used the renewal cycle as next_due.
                    # Normalize only items that have no frequency so future completions follow the right cadence.
                    interval = _FREQUENCY_DAYS[frequency]
                    if _naive_utc(item.next_due) - now > timedelta(days=interval * 2):
                        base = item.created_at or now
                        item.next_due = _naive_utc(base) + timedelta(days=interval)
                        item.due_date = item.next_due
                changed = True
            if item.next_due:
                next_due = _naive_utc(item.next_due)
                days = (next_due - now).days
                desired = ComplianceStatus.OVERDUE if days < 0 else ComplianceStatus.AT_RISK if days <= 30 else ComplianceStatus.ON_TRACK
                if _status(item.status) != desired.value:
                    item.status = desired
                    changed = True
        if changed:
            await self.db.commit()
        await self._notify_due_items(project_id, user_id, items)

    async def _notify_due_items(self, project_id: UUID, user_id: UUID, items: list[ComplianceItem]) -> None:
        now = _now()
        notifications = NotificationService(self.db)
        for item in items:
            if not item.next_due:
                continue
            days = (_naive_utc(item.next_due) - now).days
            if days < 0:
                await notifications.create_once(
                    user_id=user_id,
                    title="Compliance task overdue",
                    message=f"{item.requirement} is overdue. Review the compliance lifecycle dashboard.",
                    category="compliance",
                    severity="error",
                    project_id=project_id,
                    reference_id=str(item.id),
                    window_minutes=1440,
                )
            elif days <= 30:
                await notifications.create_once(
                    user_id=user_id,
                    title="Compliance task due soon",
                    message=f"{item.requirement} is due in approximately {max(days, 0)} days.",
                    category="compliance",
                    severity="warning",
                    project_id=project_id,
                    reference_id=str(item.id),
                    window_minutes=1440,
                )

    async def _notify_renewals(self, project_id: UUID, user_id: UUID, renewals: list[dict]) -> None:
        notifications = NotificationService(self.db)
        for renewal in renewals:
            days = int(renewal.get("days_until_renewal") or 0)
            status = renewal.get("lifecycle_status")
            if status == "OVERDUE":
                await notifications.create_once(
                    user_id=user_id,
                    title="Renewal overdue",
                    message=f"{renewal['approval_name']} renewal is overdue. Review the renewal lifecycle and external filing options.",
                    category="compliance",
                    severity="error",
                    project_id=project_id,
                    reference_id=renewal.get("case_id") or renewal.get("approval_id"),
                    window_minutes=1440,
                )
            elif status == "DUE_SOON":
                await notifications.create_once(
                    user_id=user_id,
                    title="Renewal due soon",
                    message=f"{renewal['approval_name']} renewal is due in approximately {max(days, 0)} days.",
                    category="compliance",
                    severity="warning",
                    project_id=project_id,
                    reference_id=renewal.get("case_id") or renewal.get("approval_id"),
                    window_minutes=1440,
                )

    async def _notify_renewal(self, user_id: UUID, case: RenewalCase, approval: Approval, event: str) -> None:
        title = {
            "prepared": "Renewal preparation started",
            "submitted_externally": "Renewal marked submitted externally",
            "renewed": "Renewal marked renewed",
        }.get(event, "Renewal updated")
        message = {
            "prepared": f"Renewal preparation started for {approval.name}.",
            "submitted_externally": f"{approval.name} was marked as submitted externally. No government submission was performed by the prototype.",
            "renewed": f"{approval.name} renewal was marked renewed in UDYOGSETU.",
        }.get(event, f"Renewal status changed for {approval.name}.")
        await NotificationService(self.db).create_once(
            user_id=user_id,
            title=title,
            message=message,
            category="compliance",
            severity="info" if event != "submitted_externally" else "warning",
            project_id=case.project_id,
            reference_id=str(case.id),
            window_minutes=60,
        )

    async def _ensure_owner(self, project_id: UUID, user_id: UUID) -> None:
        project = (await self.db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")
        if str(project.user_id) != str(user_id):
            raise ValueError("Not authorized to access this project")

    async def _get_owned_renewal(self, renewal_id: UUID, user_id: UUID) -> RenewalCase:
        case = (await self.db.execute(select(RenewalCase).where(RenewalCase.id == renewal_id))).scalar_one_or_none()
        if not case:
            raise ValueError("Renewal case not found")
        await self._ensure_owner(case.project_id, user_id)
        return case

    @staticmethod
    def _frequency_for_requirement(requirement: str) -> str:
        lowered = (requirement or "").lower()
        if "monthly" in lowered:
            return "monthly"
        if "quarterly" in lowered:
            return "quarterly"
        if "biannual" in lowered or "biannual" in lowered or "half-year" in lowered:
            return "biannual"
        return "annual"

    @staticmethod
    def _doc_type(document: Document) -> str:
        fields = document.extracted_fields or {}
        return str(
            (document.custom_metadata or {}).get("document_type")
            or fields.get("document_type")
            or document.file_name
        ).strip()

    @classmethod
    def _doc_payload(cls, document: Document) -> dict:
        return {
            "id": str(document.id),
            "file_name": document.file_name,
            "status": _status(document.status),
            "document_type": cls._doc_type(document),
        }

    @staticmethod
    def _item_payload(item: ComplianceItem, now: datetime) -> dict:
        next_due = _naive_utc(item.next_due) if item.next_due else None
        days_until = (next_due - now).days if next_due else None
        return {
            "id": str(item.id),
            "category": item.category,
            "requirement": item.requirement,
            "frequency": item.frequency,
            "status": _status(item.status),
            "due_date": item.due_date.isoformat() if item.due_date else None,
            "next_due": item.next_due.isoformat() if item.next_due else None,
            "last_completed": item.last_completed.isoformat() if item.last_completed else None,
            "days_until_due": days_until,
            "document_required": bool(item.document_required),
            "source": item.source,
            "can_complete": True,
        }
