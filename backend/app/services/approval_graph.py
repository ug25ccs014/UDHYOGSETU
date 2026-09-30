"""Approval dependency graph, parallel scheduling and critical-path analysis.

The service is intentionally the single source of truth for the approval
roadmap. It uses the dependencies stored on ``ApprovalRule`` rows and exposes
both a network graph and a deterministic earliest-start schedule so the UI can
show which approvals may proceed in parallel and what drives the total
estimated journey.
"""

from __future__ import annotations

from collections import defaultdict, deque
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Approval, ApprovalRule, ApprovalStatus


class ApprovalGraphService:
    """Compute a project's approval dependency graph and schedule."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_graph(self, project_id: UUID) -> dict:
        """Return graph nodes, dependency edges, parallel groups and timing data."""
        approvals = await self._get_approvals(project_id)
        rules = await self._get_rules()

        # Resolve dependencies by both the persisted rule UUID and rule name.
        # Seeded data normally uses names; tests/older data may use UUID strings.
        rule_by_id: dict[str, ApprovalRule] = {str(r.id): r for r in rules}
        rule_by_name: dict[str, ApprovalRule] = {r.name: r for r in rules}
        nodes: list[dict] = []
        for approval in approvals:
            rule = rule_by_name.get(approval.name)
            dependencies = self._resolve_dependencies(rule, rule_by_id, rule_by_name)
            days = approval.estimated_processing_days or (
                rule.estimated_processing_days if rule else 0
            ) or 0
            nodes.append(
                {
                    "id": str(approval.id),
                    "label": approval.name,
                    "department": approval.department,
                    "days": max(0, int(days)),
                    "status": self._status_value(approval.status),
                    "mandatory": bool(approval.is_mandatory),
                    "risk_level": approval.risk_level,
                    "dependencies": [dep["key"] for dep in dependencies],
                    "dependency_ids": [dep["id"] for dep in dependencies if dep["id"]],
                }
            )

        node_id_by_name = {n["label"]: n["id"] for n in nodes}
        rule_name_by_id = {str(rule.id): rule.name for rule in rules}

        edges: list[dict] = []
        edge_index = 0
        for node in nodes:
            for dependency in node["dependencies"]:
                dependency_name = rule_name_by_id.get(dependency, dependency)
                source_id = node_id_by_name.get(dependency_name)
                if not source_id:
                    continue
                if source_id == node["id"]:
                    continue
                edges.append(
                    {
                        "id": f"e{edge_index}",
                        "source": source_id,
                        "target": node["id"],
                        "dependency": dependency_name,
                    }
                )
                edge_index += 1

        schedule = self._build_schedule(nodes, edges)
        schedule_by_id = {item["id"]: item for item in schedule["items"]}

        for node in nodes:
            item = schedule_by_id.get(node["id"])
            node.update(
                {
                    "level": item["level"] if item else 0,
                    "earliest_start_day": item["start_day"] if item else 0,
                    "earliest_finish_day": item["finish_day"] if item else node["days"],
                    "execution_state": self._execution_state(node, nodes, edges),
                }
            )

        critical_ids = set(schedule["critical_path"]["approval_ids"])
        for edge in edges:
            edge["on_critical_path"] = edge["source"] in critical_ids and edge["target"] in critical_ids

        parallel_groups = self._parallel_groups(nodes, schedule["levels"], critical_ids)
        sequential_duration = sum(node["days"] for node in nodes)
        parallel_duration = schedule["critical_path"]["duration_days"]
        savings = max(0, sequential_duration - parallel_duration)

        summary = {
            "total_count": len(nodes),
            "mandatory_count": sum(1 for node in nodes if node["mandatory"]),
            "sequential_duration_days": sequential_duration,
            "parallel_duration_days": parallel_duration,
            "theoretical_time_saved_days": savings,
            "parallel_approval_count": sum(
                len(group["approval_ids"])
                for group in parallel_groups
                if len(group["approval_ids"]) > 1
            ),
            "parallel_group_count": sum(
                1 for group in parallel_groups if len(group["approval_ids"]) > 1
            ),
            "critical_path_count": len(critical_ids),
            "warning": "Timeline is an estimate based on configured processing durations and dependencies; it is not a statutory processing guarantee.",
        }

        return {
            "project_id": str(project_id),
            "nodes": nodes,
            "edges": edges,
            "parallel_groups": parallel_groups,
            "schedule": schedule["items"],
            "critical_path": schedule["critical_path"],
            "summary": summary,
            "warnings": schedule["warnings"],
        }

    async def _get_approvals(self, project_id: UUID) -> list[Approval]:
        result = await self.db.execute(
            select(Approval).where(Approval.project_id == project_id)
        )
        return list(result.scalars().all())

    async def _get_rules(self) -> list[ApprovalRule]:
        result = await self.db.execute(select(ApprovalRule))
        return list(result.scalars().all())

    @staticmethod
    def _status_value(value) -> str:
        return value.value if isinstance(value, ApprovalStatus) else str(value)

    @classmethod
    def _resolve_dependencies(
        cls,
        rule: ApprovalRule | None,
        rule_by_id: dict[str, ApprovalRule],
        rule_by_name: dict[str, ApprovalRule],
    ) -> list[dict]:
        if not rule:
            return []
        raw = rule.dependencies or []
        if isinstance(raw, str):
            raw = [raw]

        resolved: list[dict] = []
        for dependency in raw:
            key = str(dependency)
            target = rule_by_id.get(key) or rule_by_name.get(key)
            resolved.append(
                {
                    "key": target.name if target else key,
                    "id": str(target.id) if target else None,
                }
            )
        return resolved

    @staticmethod
    def _build_schedule(nodes: list[dict], edges: list[dict]) -> dict:
        """Build an earliest-start schedule and critical path for the DAG."""
        node_days = {node["id"]: node["days"] for node in nodes}
        names = {node["id"]: node["label"] for node in nodes}
        predecessors: dict[str, list[str]] = defaultdict(list)
        children: dict[str, list[str]] = defaultdict(list)
        indegree = {node["id"]: 0 for node in nodes}

        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            if source not in indegree or target not in indegree:
                continue
            predecessors[target].append(source)
            children[source].append(target)
            indegree[target] += 1

        queue = deque(sorted(node_id for node_id, degree in indegree.items() if degree == 0))
        level = {node_id: 0 for node_id in queue}
        earliest_start = {node_id: 0 for node_id in indegree}
        predecessor_for_critical: dict[str, str | None] = {
            node_id: None for node_id in indegree
        }
        topo_order: list[str] = []

        while queue:
            current = queue.popleft()
            topo_order.append(current)
            for child in sorted(children.get(current, [])):
                candidate_start = earliest_start[current] + node_days[current]
                if candidate_start > earliest_start[child]:
                    earliest_start[child] = candidate_start
                    predecessor_for_critical[child] = current
                level[child] = max(level.get(child, 0), level[current] + 1)
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)

        warnings: list[str] = []
        if len(topo_order) != len(nodes):
            cycle_nodes = sorted(node_id for node_id, degree in indegree.items() if degree > 0)
            warnings.append(
                "Dependency cycle detected; affected approvals are excluded from the calculated critical path."
            )
            for node_id in cycle_nodes:
                level[node_id] = max(level.get(node_id, 0), 0)
                earliest_start[node_id] = 0

        finish = {
            node_id: earliest_start[node_id] + node_days[node_id]
            for node_id in node_days
        }
        duration = max(finish.values(), default=0)
        end = max(finish, key=finish.get) if finish else None

        critical_ids: list[str] = []
        current = end
        visited: set[str] = set()
        while current is not None and current not in visited:
            visited.add(current)
            critical_ids.append(current)
            current = predecessor_for_critical.get(current)
        critical_ids.reverse()

        schedule_items = []
        for node_id in sorted(
            node_days,
            key=lambda item: (level.get(item, 0), earliest_start.get(item, 0), names[item]),
        ):
            schedule_items.append(
                {
                    "id": node_id,
                    "name": names[node_id],
                    "start_day": earliest_start[node_id],
                    "finish_day": finish[node_id],
                    "duration_days": node_days[node_id],
                    "level": level.get(node_id, 0),
                    "critical": node_id in set(critical_ids),
                }
            )

        levels: dict[int, list[str]] = defaultdict(list)
        for node_id in node_days:
            levels[level.get(node_id, 0)].append(node_id)

        path_nodes = [names[node_id] for node_id in critical_ids if node_id in names]
        critical_approvals = [
            {
                "id": node_id,
                "name": names[node_id],
                "days": node_days[node_id],
                "status": next(
                    (node["status"] for node in nodes if node["id"] == node_id),
                    "NOT_STARTED",
                ),
            }
            for node_id in critical_ids
            if node_id in names
        ]

        return {
            "items": schedule_items,
            "levels": {level_no: sorted(ids) for level_no, ids in levels.items()},
            "warnings": warnings,
            "critical_path": {
                "duration_days": duration,
                "approval_ids": critical_ids,
                "approvals": critical_approvals,
                "names": path_nodes,
            },
        }

    @staticmethod
    def _parallel_groups(
        nodes: list[dict], levels: dict[int, list[str]], critical_ids: set[str]
    ) -> list[dict]:
        by_id = {node["id"]: node for node in nodes}
        groups: list[dict] = []
        for level_no in sorted(levels):
            ids = [node_id for node_id in levels[level_no] if node_id in by_id]
            approvals = [
                {
                    "id": node_id,
                    "name": by_id[node_id]["label"],
                    "department": by_id[node_id]["department"],
                    "days": by_id[node_id]["days"],
                    "status": by_id[node_id]["status"],
                    "critical": node_id in critical_ids,
                }
                for node_id in ids
            ]
            groups.append(
                {
                    "stage": level_no + 1,
                    "approval_ids": ids,
                    "approvals": approvals,
                    "can_run_in_parallel": len(ids) > 1,
                    "approval_count": len(ids),
                    "stage_max_duration_days": max(
                        (approval["days"] for approval in approvals),
                        default=0,
                    ),
                }
            )
        return groups

    @staticmethod
    def _execution_state(node: dict, nodes: list[dict], edges: list[dict]) -> str:
        status = node["status"]
        if status in {"APPROVED"}:
            return "COMPLETED"
        if status in {"SUBMITTED", "UNDER_REVIEW", "INSPECTION", "QUERY_RAISED", "DRAFT"}:
            return "IN_PROGRESS"
        node_id = node["id"]
        dependency_ids = {
            edge["source"] for edge in edges if edge["target"] == node_id
        }
        by_id = {item["id"]: item for item in nodes}
        if dependency_ids and any(by_id.get(dep, {}).get("status") != "APPROVED" for dep in dependency_ids):
            return "BLOCKED"
        return "READY"
