"""Government integration status synchronization — spec §19.

A submitted application is tracked locally via ``GovernmentApplication``.
A periodic (or on-demand) sync polls the government integration layer for the
live status of each tracked application, updates that record and the related
``Approval``, and raises an in-app notification when the status changes.

On a real deployment this would be a scheduler-driven background worker. Here
it is exposed as an explicit service + an API endpoint so the E2E flow and
officer dashboard can trigger and observe the sync without a cron daemon.
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from app.models import Approval, GovernmentApplication, Project
from app.services.gateway_service import GatewayService

logger = logging.getLogger(__name__)

# Map government statuses onto our approval workflow statuses.
_STATUS_MAP = {
    "SUBMITTED": "SUBMITTED",
    "UNDER_REVIEW": "UNDER_REVIEW",
    "QUERY_RAISED": "QUERY_RAISED",
    "INSPECTION": "INSPECTION",
    "APPROVED": "APPROVED",
    "REJECTED": "REJECTED",
}


class GovSyncService:
    """Poll and reconcile government application status."""

    def __init__(self, db, gateway: GatewayService | None = None):
        self.db = db
        self.gateway = gateway or GatewayService()

    async def track(self, approval: Approval, system: str, gov_application_id: str) -> GovernmentApplication:
        """Record a government application link for an approval."""
        result = await self.db.execute(
            select(GovernmentApplication).where(
                GovernmentApplication.approval_id == approval.id,
                GovernmentApplication.system == system,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.government_application_id = gov_application_id
            record = existing
        else:
            record = GovernmentApplication(
                approval_id=approval.id,
                project_id=approval.project_id,
                system=system,
                government_application_id=gov_application_id,
            )
            self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def sync_one(self, record: GovernmentApplication) -> dict:
        """Poll the gateway for one application and reconcile its status."""
        env = await self.gateway.get_status(record.system, record.government_application_id)
        if env is None:
            env = {}
        if not isinstance(env, dict):
            env = {}
        data = env.get("data") if isinstance(env.get("data"), dict) else {}
        gov_status = data.get("status") or env.get("status")
        if not gov_status:
            return {
                "government_application_id": record.government_application_id,
                "unchanged": True,
                "error": env.get("error") if isinstance(env, dict) else "no status",
            }

        changed = gov_status != record.last_synced_status
        record.last_synced_status = gov_status
        record.last_synced_at = datetime.utcnow()
        record.raw_response = {"data": dict(data) if isinstance(data, dict) else {}}
        await self.db.commit()

        if record.approval_id:
            approval = await self.db.get(Approval, record.approval_id)
            if approval:
                mapped = _STATUS_MAP.get(gov_status)
                if mapped and changed:
                    await self._apply_approval_status(approval, mapped, gov_status, record)
                elif not mapped and changed:
                    logger.warning("Unmapped gov status %s for %s", gov_status, record.government_application_id)

        return {
            "government_application_id": record.government_application_id,
            "system": record.system,
            "previous_status": record.last_synced_status,
            "current_status": gov_status,
            "changed": changed,
            "query": data.get("query") if isinstance(data, dict) else None,
        }

    async def _apply_approval_status(self, approval: Approval, mapped: str, gov_status: str, record: GovernmentApplication) -> None:
        old = approval.status.value if hasattr(approval.status, "value") else str(approval.status)
        if old == mapped:
            return

        # Use the workflow engine where possible; fall back to a direct sync
        # for statuses the entrepreneur-side workflow does not allow.
        from app.services.approval_workflow import ApprovalWorkflowEngine
        engine = ApprovalWorkflowEngine("ADMIN")
        try:
            from app.models import ApprovalStatus
            target = ApprovalStatus[mapped]
            decision = engine.apply(approval, target)
            if not decision.allowed:
                approval.status = target
                if target is ApprovalStatus.APPROVED:
                    approval.approved_at = approval.approved_at or datetime.utcnow()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Workflow apply failed during gov sync: %s (falling back)", exc)
            approval.status = mapped
        await self.db.commit()

        # Notify the project owner of the status change.
        try:
            owner = None
            result = await self.db.execute(select(Project).where(Project.id == approval.project_id))
            owner = result.scalar_one_or_none()
            if owner:
                from app.notifications.service import NotificationService
                await NotificationService(self.db).create(
                    str(owner.user_id),
                    "Application Status Updated",
                    f"Your {approval.name} application ({record.government_application_id}) "
                    f"is now {mapped} per {record.system}.",
                    category="approval",
                    severity="info" if mapped != "REJECTED" else "warning",
                    project_id=approval.project_id,
                    reference_id=str(approval.id),
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to notify owner on gov sync: %s", exc)

    async def sync_all(self) -> dict:
        """Sync every tracked government application."""
        result = await self.db.execute(select(GovernmentApplication))
        records = result.scalars().all()
        outcomes = [await self.sync_one(r) for r in records]
        changed = sum(1 for o in outcomes if o.get("changed"))
        return {"synced": len(outcomes), "changed": changed, "items": outcomes}

    async def sync_for_project(self, project_id: UUID) -> dict:
        result = await self.db.execute(
            select(GovernmentApplication).where(GovernmentApplication.project_id == project_id)
        )
        records = result.scalars().all()
        outcomes = [await self.sync_one(r) for r in records]
        return {"project_id": str(project_id), "synced": len(outcomes), "items": outcomes}
