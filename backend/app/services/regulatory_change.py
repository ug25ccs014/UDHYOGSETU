"""Regulatory change center services.

Builds an applicant- and officer-friendly view over the existing
``KnowledgeDocument`` versioning model. The service is advisory: it identifies
potentially impacted approvals/projects and summarizes document differences,
but it does not make a statutory determination.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Approval, ApprovalStatus, KnowledgeDocument, Project


_VERSION_FIELDS = (
    "title",
    "department",
    "document_type",
    "version",
    "jurisdiction",
    "sector",
    "effective_date",
    "effective_to",
)
_ACTIVE_APPROVALS = {
    ApprovalStatus.NOT_STARTED.value,
    ApprovalStatus.DRAFT.value,
    ApprovalStatus.SUBMITTED.value,
    ApprovalStatus.UNDER_REVIEW.value,
    ApprovalStatus.QUERY_RAISED.value,
    ApprovalStatus.INSPECTION.value,
    ApprovalStatus.APPROVED.value,
}
_STATUS_ORDER = {"ACTIVE": 0, "UPCOMING": 1, "UNKNOWN": 2, "EXPIRED": 3}
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")


def _short(value: str | None) -> str:
    return value or "current"


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _as_naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


class RegulatoryChangeService:
    """Build version diffs and potential impact signals from the knowledge base."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def diff(self, document_id: UUID, project_id: UUID | None = None) -> dict:
        doc = await self._get_document(document_id)
        if not doc:
            return {"error": "Regulation not found"}

        previous = await self._get_previous(doc)
        text_diff = self._text_diff(previous, doc)
        impact = await self._impact(doc, project_id=project_id)

        return {
            "document_id": str(doc.id),
            "title": doc.title,
            "department": doc.department,
            "document_type": doc.document_type,
            "version": _short(doc.version),
            "supersedes_document_id": str(previous.id) if previous else None,
            "supersedes_version": _short(previous.version) if previous else None,
            "effective_date": doc.effective_date.isoformat() if doc.effective_date else None,
            "effective_to": doc.effective_to.isoformat() if doc.effective_to else None,
            "effective_status": self._effective_status(doc),
            "is_latest": bool(doc.is_latest),
            "changed_fields": self._field_changes(previous, doc),
            "text_changed": text_diff["changed"],
            "text_change_summary": text_diff["summary"],
            "similarity": text_diff["similarity"],
            "change_items": text_diff["change_items"],
            "impact": impact,
            "source": {
                "url": doc.source_url,
                "label": "Knowledge base source" if doc.source_url else "Source URL not provided in the prototype knowledge base",
            },
            "note": (
                "Advisory analysis: potential impact and change summaries are based on the configured knowledge base "
                "and existing approval records. They are not a statutory determination or legal interpretation."
            ),
        }

    async def recent_changes(
        self,
        limit: int = 20,
        department: str | None = None,
        effective_status: str | None = None,
    ) -> list[dict]:
        stmt = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.supersedes_document_id.isnot(None))
            .order_by(KnowledgeDocument.created_at.desc())
            .limit(min(max(limit, 1), 100))
        )
        if department:
            stmt = stmt.where(KnowledgeDocument.department.ilike(f"%{department.strip()}%"))

        docs = list((await self.db.execute(stmt)).scalars().all())
        items = []
        for doc in docs:
            status_value = self._effective_status(doc)
            if effective_status and status_value != effective_status.upper():
                continue
            previous = await self._get_previous(doc)
            text_diff = self._text_diff(previous, doc)
            impact = await self._impact(doc)
            items.append(self._summary(doc, previous, text_diff, impact))

        items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        items.sort(key=lambda item: _STATUS_ORDER.get(item["effective_status"], 9))
        return items

    async def project_changes(self, project_id: UUID, limit: int = 20) -> list[dict]:
        """Return recent version changes with a potential match to a specific project."""
        stmt = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.supersedes_document_id.isnot(None))
            .order_by(KnowledgeDocument.created_at.desc())
            .limit(100)
        )
        docs = list((await self.db.execute(stmt)).scalars().all())
        items = []
        for doc in docs:
            previous = await self._get_previous(doc)
            text_diff = self._text_diff(previous, doc)
            impact = await self._impact(doc, project_id=project_id)
            current = impact.get("current_project") or {}
            if not current.get("potentially_affected"):
                continue
            items.append(self._summary(doc, previous, text_diff, impact))
            if len(items) >= min(max(limit, 1), 100):
                break
        return items

    async def _get_document(self, document_id: UUID) -> KnowledgeDocument | None:
        result = await self.db.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
        )
        return result.scalar_one_or_none()

    async def _get_previous(self, doc: KnowledgeDocument | None) -> KnowledgeDocument | None:
        if not doc or not doc.supersedes_document_id:
            return None
        result = await self.db.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.id == doc.supersedes_document_id)
        )
        return result.scalar_one_or_none()

    async def _impact(self, doc: KnowledgeDocument, project_id: UUID | None = None) -> dict:
        if not doc.department:
            return {
                "potentially_affected": False,
                "approval_count": 0,
                "project_count": 0,
                "departments": [],
                "reason": "The knowledge document has no department metadata, so impact could not be mapped automatically.",
                "current_project": None,
            }

        stmt = (
            select(Approval, Project)
            .join(Project, Project.id == Approval.project_id)
            .where(
                Approval.department.ilike(doc.department),
                Approval.is_active.is_(True),
            )
        )
        rows = list((await self.db.execute(stmt)).all())

        matches = []
        for approval, project in rows:
            if approval.status is not None and getattr(approval.status, "value", str(approval.status)) not in _ACTIVE_APPROVALS:
                continue
            if doc.sector and approval.sector and doc.sector.strip().lower() != approval.sector.strip().lower():
                continue
            matches.append((approval, project))

        departments = sorted({approval.department for approval, _ in matches if approval.department})
        project_ids = {str(project.id) for _, project in matches}

        impact = {
            "potentially_affected": bool(matches),
            "approval_count": len(matches),
            "project_count": len(project_ids),
            "departments": departments,
            "reason": (
                f"Matched {len(matches)} active approval record(s) in {doc.department}. "
                "This is a potential-impact signal based on department/sector metadata."
                if matches
                else "No active approval records matched the document's department/sector metadata."
            ),
            "current_project": None,
        }

        if project_id:
            current = [
                {
                    "approval_id": str(approval.id),
                    "approval_name": approval.name,
                    "department": approval.department,
                    "status": approval.status.value if hasattr(approval.status, "value") else str(approval.status),
                }
                for approval, project in matches
                if project.id == project_id
            ]
            project = await self._get_project(project_id)
            impact["current_project"] = {
                "project_id": str(project_id),
                "project_name": project.name if project else None,
                "potentially_affected": bool(current),
                "matched_approvals": current,
            }

        return impact

    async def _get_project(self, project_id: UUID) -> Project | None:
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        return result.scalar_one_or_none()

    def _summary(self, doc, previous, text_diff, impact) -> dict:
        return {
            "document_id": str(doc.id),
            "title": doc.title,
            "department": doc.department,
            "document_type": doc.document_type,
            "version": _short(doc.version),
            "previous_version": _short(previous.version) if previous else None,
            "effective_date": doc.effective_date.isoformat() if doc.effective_date else None,
            "effective_to": doc.effective_to.isoformat() if doc.effective_to else None,
            "effective_status": self._effective_status(doc),
            "is_latest": bool(doc.is_latest),
            "text_changed": text_diff["changed"],
            "text_change_summary": text_diff["summary"],
            "similarity": text_diff["similarity"],
            "change_items": text_diff["change_items"][:5],
            "changed_field_count": len(self._field_changes(previous, doc)),
            "impact": {
                "potentially_affected": impact["potentially_affected"],
                "approval_count": impact["approval_count"],
                "project_count": impact["project_count"],
                "department": doc.department,
                "reason": impact["reason"],
            },
            "source_url": doc.source_url,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }

    def _effective_status(self, doc: KnowledgeDocument) -> str:
        now = _utc_now_naive()
        effective_date = _as_naive_utc(doc.effective_date)
        effective_to = _as_naive_utc(doc.effective_to)
        if effective_to and effective_to < now:
            return "EXPIRED"
        if effective_date and effective_date > now:
            return "UPCOMING"
        if effective_date and effective_date <= now and (effective_to is None or effective_to >= now):
            return "ACTIVE"
        return "UNKNOWN"

    @staticmethod
    def _field_changes(previous: KnowledgeDocument | None, doc: KnowledgeDocument) -> list[dict]:
        if previous is None:
            return []
        changes = []
        for field in _VERSION_FIELDS:
            old = getattr(previous, field, None)
            new = getattr(doc, field, None)
            if old != new:
                if isinstance(old, datetime):
                    old = old.isoformat()
                if isinstance(new, datetime):
                    new = new.isoformat()
                changes.append({"field": field, "from": old, "to": new})
        return changes

    @classmethod
    def _text_diff(cls, previous: KnowledgeDocument | None, doc: KnowledgeDocument) -> dict:
        if previous is None:
            return {
                "changed": True,
                "summary": "No previous version to compare.",
                "similarity": 0.0,
                "change_items": [],
            }

        old_text = (previous.text or "").strip()
        new_text = (doc.text or "").strip()
        similarity = round(SequenceMatcher(None, old_text, new_text).ratio(), 3)
        changed = old_text != new_text
        if not changed:
            return {
                "changed": False,
                "summary": "Text unchanged.",
                "similarity": similarity,
                "change_items": [],
            }

        sections = cls._sections(old_text, new_text)
        items: list[dict] = []
        for section in sections:
            before = section["before"]
            after = section["after"]
            if before == after:
                continue
            if not before:
                items.append({"type": "ADDED", "section": section["title"], "new_text": cls._excerpt(after)})
                continue
            if not after:
                items.append({"type": "REMOVED", "section": section["title"], "old_text": cls._excerpt(before)})
                continue
            if before != after:
                items.append({
                    "type": "MODIFIED",
                    "section": section["title"],
                    "old_text": cls._excerpt(before),
                    "new_text": cls._excerpt(after),
                })

        if len(new_text) > len(old_text):
            summary = f"Text expanded (+{len(new_text) - len(old_text)} characters)."
        else:
            summary = f"Text shortened ({len(old_text) - len(new_text)} characters removed)."

        return {
            "changed": True,
            "summary": summary,
            "similarity": similarity,
            "change_items": items[:12],
        }

    @classmethod
    def _sections(cls, old_text: str, new_text: str) -> list[dict]:
        old_map = cls._section_map(old_text)
        new_map = cls._section_map(new_text)
        titles = list(dict.fromkeys([*old_map.keys(), *new_map.keys()]))
        if not titles:
            return [{"title": "Document text", "before": old_text, "after": new_text}]
        return [
            {"title": title, "before": old_map.get(title, ""), "after": new_map.get(title, "")}
            for title in titles
        ]

    @staticmethod
    def _section_map(text: str) -> dict[str, str]:
        lines = text.splitlines()
        sections: dict[str, list[str]] = {}
        current = "Document text"
        sections[current] = []
        for line in lines:
            match = _HEADING_RE.match(line)
            if match:
                current = match.group(1).strip()
                sections.setdefault(current, [])
                continue
            sections.setdefault(current, []).append(line.strip())
        return {title: "\n".join(line for line in lines if line).strip() for title, lines in sections.items()}

    @staticmethod
    def _excerpt(text: str, limit: int = 320) -> str:
        compact = " ".join(text.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 1].rstrip() + "…"
