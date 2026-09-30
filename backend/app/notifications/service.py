"""Notifications engine (in-app).

Creates notifications for user-facing events and exposes an owner-scoped,
queryable notification feed. Notifications are intentionally in-app only;
external email/SMS/push delivery is outside this prototype's authority boundary.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Approval, Notification

logger = logging.getLogger(__name__)


class NotificationService:
    """Create, query, deduplicate and acknowledge in-app notifications."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _uuid(value: str | UUID) -> UUID:
        return value if isinstance(value, UUID) else UUID(str(value))

    @staticmethod
    def action_path(notification: Notification) -> str | None:
        """Map a notification to an existing first-party UDYOGSETU destination."""
        category = (notification.category or "general").lower()
        ref = notification.reference_id
        project_id = str(notification.project_id) if notification.project_id else None

        if category in {"approval", "query", "application", "sla", "risk"} and ref:
            return f"/dashboard/applications/{ref}"
        if category == "inspection":
            return "/dashboard/inspections"
        if category == "grievance":
            return "/dashboard/grievances"
        if category == "compliance" and project_id:
            return f"/dashboard/{project_id}/compliance"
        if category in {"scheme", "incentive"} and project_id:
            return f"/dashboard/{project_id}/schemes"
        if category == "regulatory":
            return f"/dashboard/regulatory?change={ref}" if ref else "/dashboard/regulatory"
        if category == "profile":
            return "/dashboard/profile"
        return None

    @classmethod
    def serialize(cls, notification: Notification) -> dict:
        payload = notification.to_dict()
        payload["action_path"] = cls.action_path(notification)
        return payload

    async def create(
        self,
        user_id: str | UUID,
        title: str,
        message: str,
        category: str = "general",
        severity: str = "info",
        project_id: str | UUID | None = None,
        reference_id: str | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=self._uuid(user_id),
            title=title,
            message=message,
            category=(category or "general").lower(),
            severity=(severity or "info").lower(),
            project_id=self._uuid(project_id) if project_id else None,
            reference_id=reference_id,
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def create_once(
        self,
        user_id: str | UUID,
        title: str,
        message: str,
        category: str = "general",
        severity: str = "info",
        project_id: str | UUID | None = None,
        reference_id: str | None = None,
        window_minutes: int = 30,
    ) -> Notification:
        """Create only when the same event has not been persisted recently.

        This prevents repeated polling/retry cycles from flooding the notification
        center while still allowing a later, genuinely new event with the same
        title/reference to appear.
        """
        since = datetime.utcnow() - timedelta(minutes=max(1, window_minutes))
        stmt = (
            select(Notification)
            .where(
                Notification.user_id == self._uuid(user_id),
                Notification.title == title,
                Notification.category == (category or "general").lower(),
                Notification.reference_id == reference_id,
                Notification.created_at >= since,
            )
            .order_by(Notification.created_at.desc())
            .limit(1)
        )
        if project_id:
            stmt = stmt.where(Notification.project_id == self._uuid(project_id))

        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        return await self.create(
            user_id=user_id,
            title=title,
            message=message,
            category=category,
            severity=severity,
            project_id=project_id,
            reference_id=reference_id,
        )

    async def list_for_user(
        self,
        user_id: str | UUID,
        unread_only: bool = False,
        category: str | None = None,
        severity: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        limit = min(max(limit, 1), 100)
        offset = max(offset, 0)
        stmt = select(Notification).where(Notification.user_id == self._uuid(user_id))
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))
        if category:
            stmt = stmt.where(Notification.category == category.lower())
        if severity:
            stmt = stmt.where(Notification.severity == severity.lower())
        stmt = (
            stmt.order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = await self.db.execute(stmt)
        return list(rows.scalars().all())

    async def total_for_user(
        self,
        user_id: str | UUID,
        unread_only: bool = False,
        category: str | None = None,
        severity: str | None = None,
    ) -> int:
        stmt = select(func.count(Notification.id)).where(Notification.user_id == self._uuid(user_id))
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))
        if category:
            stmt = stmt.where(Notification.category == category.lower())
        if severity:
            stmt = stmt.where(Notification.severity == severity.lower())
        result = await self.db.execute(stmt)
        return int(result.scalar_one() or 0)

    async def unread_count(self, user_id: str | UUID) -> int:
        return await self.total_for_user(user_id, unread_only=True)

    async def summary(self, user_id: str | UUID) -> dict:
        uid = self._uuid(user_id)
        total_result = await self.db.execute(
            select(func.count(Notification.id)).where(Notification.user_id == uid)
        )
        unread_result = await self.db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == uid,
                Notification.is_read.is_(False),
            )
        )
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_result = await self.db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == uid,
                Notification.created_at >= recent_cutoff,
            )
        )
        category_result = await self.db.execute(
            select(Notification.category, func.count(Notification.id))
            .where(Notification.user_id == uid)
            .group_by(Notification.category)
        )
        severity_result = await self.db.execute(
            select(Notification.severity, func.count(Notification.id))
            .where(Notification.user_id == uid)
            .group_by(Notification.severity)
        )
        return {
            "total": int(total_result.scalar_one() or 0),
            "unread": int(unread_result.scalar_one() or 0),
            "recent_24h": int(recent_result.scalar_one() or 0),
            "by_category": {str(k or "general"): int(v) for k, v in category_result.all()},
            "by_severity": {str(k or "info"): int(v) for k, v in severity_result.all()},
        }

    async def mark_read(self, user_id: str | UUID, notification_id: str | UUID) -> bool:
        try:
            nid = self._uuid(notification_id)
        except (ValueError, TypeError):
            return False
        # Idempotent acknowledgement: an already-read owned notification is
        # still considered successfully acknowledged.
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.id == nid,
                Notification.user_id == self._uuid(user_id),
            )
            .values(
                is_read=True,
                read_at=func.coalesce(Notification.read_at, datetime.utcnow()),
            )
        )
        await self.db.commit()
        return result.rowcount > 0

    async def mark_all_read(self, user_id: str | UUID, category: str | None = None) -> int:
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == self._uuid(user_id),
                Notification.is_read.is_(False),
            )
            .values(is_read=True, read_at=datetime.utcnow())
        )
        if category:
            stmt = stmt.where(Notification.category == category.lower())
        result = await self.db.execute(stmt)
        await self.db.commit()
        return int(result.rowcount or 0)

    # ------------------------------------------------------------------
    # Domain triggers
    # ------------------------------------------------------------------
    async def notify_approval_status(self, approval: Approval):
        """Create a deduplicated notification for a material approval change."""
        status = approval.status.value if hasattr(approval.status, "value") else str(approval.status)
        owner_id = None
        try:
            from app.models import Project
            result = await self.db.execute(select(Project).where(Project.id == approval.project_id))
            project = result.scalar_one_or_none()
            owner_id = project.user_id if project else None
        except Exception as exc:  # noqa: BLE001 - owner lookup must not break the trigger
            logger.debug("Owner lookup failed for approval %s: %s", approval.id, exc)
        if not owner_id:
            return

        if status in ("SUBMITTED", "APPROVED", "REJECTED", "QUERY_RAISED", "INSPECTION"):
            severity = {
                "APPROVED": "success",
                "REJECTED": "error",
                "QUERY_RAISED": "warning",
                "INSPECTION": "info",
            }.get(status, "info")
            try:
                await self.create_once(
                    owner_id,
                    "Application Status Updated",
                    f"Your application for {approval.name} is now {status.replace('_', ' ').lower()}.",
                    category="approval",
                    severity=severity,
                    project_id=approval.project_id,
                    reference_id=str(approval.id),
                    window_minutes=10,
                )
            except Exception:  # noqa: BLE001
                logger.warning("Failed to create notification for %s", approval.id)

    async def sla_alert_for_project(self, project_id: UUID) -> None:
        """Notify the owner about approvals that have reached their SLA."""
        rows = await self.db.execute(select(Approval).where(Approval.project_id == project_id))
        approvals = list(rows.scalars().all())
        for approval in approvals:
            status = approval.status.value if hasattr(approval.status, "value") else str(approval.status)
            if status not in ("SUBMITTED", "UNDER_REVIEW"):
                continue
            est = approval.estimated_processing_days or 0
            submitted = approval.submitted_at
            if not submitted or not est:
                continue
            elapsed = (datetime.utcnow() - submitted).days
            if elapsed >= est:
                try:
                    from app.models import Project
                    project = (await self.db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
                    if not project:
                        continue
                    await self.create_once(
                        project.user_id,
                        "SLA Breach Alert",
                        f"Your {approval.name} application has reached its configured {est}-day processing window without a final decision.",
                        category="sla",
                        severity="error",
                        project_id=project_id,
                        reference_id=str(approval.id),
                        window_minutes=1440,
                    )
                except Exception:  # noqa: BLE001 - alert side channel
                    logger.warning("Failed to create SLA alert for %s", approval.id)
