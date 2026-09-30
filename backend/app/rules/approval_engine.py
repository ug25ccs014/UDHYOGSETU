from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Approval, ApprovalRule, ApprovalStatus, Project


class ApprovalEngine:
    """Intelligent approval determination engine"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def determine_approvals(self, project_id: UUID) -> list[dict]:
        """
        Determine applicable approvals based on project profile
        Uses rule-based logic with optional AI explanations
        """
        # Get project
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            return []
        
        # Get all active rules
        result = await self.db.execute(
            select(ApprovalRule).where(ApprovalRule.is_active == True)
        )
        rules = result.scalars().all()
        
        # Evaluate rules
        applicable_approvals = []
        for rule in rules:
            if self._evaluate_rule(rule, project):
                # Create approval record
                approval = Approval(
                    project_id=project_id,
                    name=rule.name,
                    department=rule.department,
                    sector=rule.sector,
                    is_mandatory=rule.is_mandatory,
                    risk_level=rule.risk_level,
                    estimated_processing_days=rule.estimated_processing_days,
                    renewal_period_days=rule.renewal_period_days,
                    source=rule.source,
                    source_url=rule.source_url,
                    status=ApprovalStatus.NOT_STARTED,
                )
                
                self.db.add(approval)
                
                applicable_approvals.append({
                    "id": str(approval.id),
                    "name": rule.name,
                    "department": rule.department,
                    "is_mandatory": rule.is_mandatory,
                    "risk_level": rule.risk_level,
                    "estimated_processing_days": rule.estimated_processing_days,
                    "dependencies": rule.dependencies,
                    "required_documents": rule.required_documents,
                })
        
        await self.db.commit()
        return applicable_approvals
    
    def _evaluate_rule(self, rule: ApprovalRule, project: Project) -> bool:
        """Evaluate if a rule applies to a project"""
        conditions = rule.conditions

        if not conditions:
            return True

        return self._evaluate_conditions(conditions, project)

    def evaluate_rule_details(self, rule: ApprovalRule, project: Project) -> dict:
        """Deterministically evaluate a single rule against a project and return
        a human-readable breakdown of matched / unmet conditions.

        Used by the Explore module's "Check Applicability" so the result can be
        explained rather than presented as an opaque boolean.
        """
        conditions = rule.conditions
        if not conditions:
            return {
                "applies": True,
                "matched": ["This service is required for every project"],
                "failed": [],
            }

        matched, failed = self._walk_conditions(conditions, project)
        return {"applies": not failed, "matched": matched, "failed": failed}

    def _walk_conditions(self, conditions, project) -> tuple[list[str], list[str]]:
        """Recursively evaluate a condition tree, collecting matched/failed
        descriptions. ``failed`` is empty iff the whole tree evaluates True."""
        if not isinstance(conditions, dict):
            return [], ["Invalid condition block"]

        condition_type = conditions.get("type")

        if condition_type == "AND":
            matched, failed = [], []
            for sub in conditions.get("conditions", []):
                m, f = self._walk_conditions(sub, project)
                matched += m
                failed += f
            return matched, failed

        if condition_type == "OR":
            subs = conditions.get("conditions", [])
            results = [self._walk_conditions(s, project) for s in subs]
            if any(not f for _, f in results):
                matched = [d for (m, f), d in zip(results, subs) if not f and m]
                return matched, []
            return [], [self._describe(sub) for sub in subs]

        if condition_type == "NOT":
            m, f = self._walk_conditions(conditions.get("condition"), project)
            if f:
                return [self._describe(conditions.get("condition")) + " (negated)"], []
            return [], [self._describe(conditions.get("condition")) + " (negated)"]

        if condition_type == "COMPARISON":
            ok = self._evaluate_comparison(conditions, project)
            desc = self._describe(conditions)
            return ([desc] if ok else [], [desc] if not ok else [])

        return [], [f"Unsupported condition type: {condition_type}"]

    def _describe(self, condition: dict) -> str:
        """Render a comparison condition as a short plain-english clause."""
        field = condition.get("field", "?")
        operator = condition.get("operator", "?")
        value = condition.get("value")
        op_label = {
            "equals": "equals",
            "not_equals": "does not equal",
            "contains": "contains",
            "in": "is one of",
            "greater_than": "is greater than",
            "less_than": "is less than",
        }.get(operator, operator)
        return f"{field} {op_label} {value!r}"
    
    def _evaluate_conditions(self, conditions: dict, project: Project) -> bool:
        """Recursively evaluate condition logic"""
        if "type" in conditions:
            condition_type = conditions.get("type")
            
            if condition_type == "AND":
                return all(
                    self._evaluate_conditions(c, project)
                    for c in conditions.get("conditions", [])
                )
            
            elif condition_type == "OR":
                return any(
                    self._evaluate_conditions(c, project)
                    for c in conditions.get("conditions", [])
                )
            
            elif condition_type == "NOT":
                return not self._evaluate_conditions(
                    conditions.get("condition"), project
                )
            
            elif condition_type == "COMPARISON":
                return self._evaluate_comparison(conditions, project)
        
        return False
    
    def _evaluate_comparison(self, condition: dict, project: Project) -> bool:
        """Evaluate a single comparison condition"""
        field = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")
        
        # Get project field value
        project_value = getattr(project, field, None)
        
        if project_value is None:
            return False
        
        # Evaluate comparison
        if operator == "equals":
            return project_value == value
        elif operator == "contains":
            return value in project_value if isinstance(project_value, str) else False
        elif operator == "greater_than":
            return project_value > value
        elif operator == "less_than":
            return project_value < value
        elif operator == "in":
            return project_value in value if isinstance(value, list) else False
        elif operator == "not_equals":
            return project_value != value
        
        return False
    
    async def build_dependency_graph(self, project_id: UUID) -> dict:
        """
        Build approval dependency graph
        Returns graph structure for React Flow visualization
        """
        result = await self.db.execute(
            select(Approval).where(Approval.project_id == project_id)
        )
        approvals = result.scalars().all()
        
        nodes = [
            {
                "id": "project",
                "data": {"label": "Project Initiated"},
                "position": {"x": 0, "y": 0},
                "type": "input",
            }
        ]
        
        edges = []
        y_position = 100
        
        for approval in approvals:
            node_id = str(approval.id)
            nodes.append({
                "id": node_id,
                "data": {
                    "label": approval.name,
                    "department": approval.department,
                    "status": approval.status,
                    "days": approval.estimated_processing_days,
                },
                "position": {"x": 0, "y": y_position},
                "type": "default",
            })
            
            # Connect from project
            edges.append({
                "id": f"project-{node_id}",
                "source": "project",
                "target": node_id,
                "type": "smoothstep",
                "animated": approval.status == ApprovalStatus.UNDER_REVIEW,
            })
            
            y_position += 100
        
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total": len(approvals),
                "mandatory": sum(1 for a in approvals if a.is_mandatory),
                "parallel_groups": self._identify_parallel_groups(approvals),
            }
        }
    
    def _identify_parallel_groups(self, approvals: list[Approval]) -> list[list[str]]:
        """Identify approvals that can run in parallel"""
        # Simple implementation: approvals with no dependencies can run in parallel
        groups = []
        parallel_group = []
        
        for approval in approvals:
            if not approval.dependencies or len(approval.dependencies) == 0:
                parallel_group.append(str(approval.id))
        
        if parallel_group:
            groups.append(parallel_group)
        
        return groups
