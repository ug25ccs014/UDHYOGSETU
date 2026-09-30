"""Scenario modelling for project-planning decisions.

The simulator has two layers:

* Backward-compatible pure functions used by existing callers/tests.
* A read-only, project-aware simulation that reuses the approval rule engine,
  approval dependency scheduler and canonical incentive matcher. No project,
  approval, document or government-system data is mutated by a simulation.

All results are advisory planning scenarios, not statutory determinations,
application outcomes, processing guarantees, or government decisions.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Approval, ApprovalRule, Project
from app.rules.approval_engine import ApprovalEngine
from app.services.approval_graph import ApprovalGraphService
from app.services.incentive_matcher import IncentiveMatcher


class ScenarioSimulator:
    """Simulate project changes and report their planning impact."""

    SUPPORTED_SCENARIOS = {
        "location_change": {
            "label": "Change project location",
            "description": "Model the planning impact of moving the project to another state/district.",
            "parameters": ["new_state", "new_district", "new_city"],
        },
        "sector_upgrade": {
            "label": "Change sector / industry",
            "description": "Model how a sector or industry change affects configured approvals and incentives.",
            "parameters": ["new_sector", "new_industry"],
        },
        "investment_change": {
            "label": "Change investment",
            "description": "Model how a changed investment amount affects scheme matches and configured project signals.",
            "parameters": ["new_investment_amount"],
        },
        "capacity_expansion": {
            "label": "Increase production capacity",
            "description": "Model capacity expansion using a planning input for current and proposed capacity.",
            "parameters": ["current_capacity", "new_capacity"],
        },
        "boiler_addition": {
            "label": "Add or remove boiler",
            "description": "Model the approval and document impact of adding or removing a boiler.",
            "parameters": ["has_boiler"],
        },
        "hazardous_materials": {
            "label": "Add or remove hazardous materials",
            "description": "Model the approval/risk signal impact of hazardous-material handling.",
            "parameters": ["hazardous_materials"],
        },
        "timeline_compression": {
            "label": "Compress target timeline",
            "description": "Model the feasibility of targeting a shorter approval journey.",
            "parameters": ["target_days"],
        },
    }

    def __init__(self, db: AsyncSession | None = None):
        self.db = db

    @classmethod
    def scenario_catalog(cls) -> list[dict]:
        return [
            {"type": scenario_type, **metadata}
            for scenario_type, metadata in cls.SUPPORTED_SCENARIOS.items()
        ]

    # ------------------------------------------------------------------
    # Existing pure simulation API (kept backward compatible)
    # ------------------------------------------------------------------
    def simulate_location_change(self, original_project: dict, new_location: dict) -> dict:
        impact = {
            "scenario": "location_change",
            "original_location": original_project.get("location"),
            "new_location": new_location.get("name"),
            "changes": {
                "approvals_added": [],
                "approvals_removed": [],
                "timeline_change_days": 0,
                "cost_impact": 0,
            },
            "affected_approvals": [],
        }
        location_approvals = self._get_location_approvals(new_location)
        original_approvals = self._get_location_approvals(original_project.get("location", {}))
        impact["changes"]["approvals_added"] = [a for a in location_approvals if a not in original_approvals]
        impact["changes"]["approvals_removed"] = [a for a in original_approvals if a not in location_approvals]
        added_days = len(impact["changes"]["approvals_added"]) * 30
        removed_days = len(impact["changes"]["approvals_removed"]) * 30
        impact["changes"]["timeline_change_days"] = added_days - removed_days
        impact["changes"]["cost_impact"] = (added_days - removed_days) * 500
        impact["affected_approvals"] = impact["changes"]["approvals_added"]
        return impact

    def simulate_sector_upgrade(self, original_project: dict, new_sector: str) -> dict:
        impact = {
            "scenario": "sector_upgrade",
            "original_sector": original_project.get("sector"),
            "new_sector": new_sector,
            "changes": {
                "approvals_required": [],
                "estimated_additional_timeline": 0,
                "estimated_additional_cost": 0,
                "pollution_category_change": None,
            },
        }
        new_approvals = self._get_sector_approvals(new_sector)
        original_approvals = self._get_sector_approvals(original_project.get("sector", "manufacturing"))
        additional = [a for a in new_approvals if a not in original_approvals]
        impact["changes"]["approvals_required"] = additional
        impact["changes"]["estimated_additional_timeline"] = len(additional) * 40
        impact["changes"]["estimated_additional_cost"] = len(additional) * 2000
        original_category = self._get_pollution_category(original_project.get("sector", ""))
        new_category = self._get_pollution_category(new_sector)
        if new_category != original_category:
            impact["changes"]["pollution_category_change"] = new_category
        return impact

    def simulate_capacity_expansion(self, original_project: dict, new_capacity: float) -> dict:
        original_capacity = original_project.get("capacity", 0)
        increase_percent = round(((new_capacity - original_capacity) / original_capacity * 100), 2) if original_capacity else 0
        impact = {
            "scenario": "capacity_expansion",
            "original_capacity": original_capacity,
            "new_capacity": new_capacity,
            "capacity_increase_percent": increase_percent,
            "changes": {
                "new_approvals_required": [],
                "modified_approvals": [],
                "timeline_extension_days": 0,
                "cost_increase": 0,
            },
        }
        if original_capacity and new_capacity <= 0:
            impact["changes"]["modified_approvals"] = ["Capacity value must be positive for expansion modelling"]
            return impact
        baseline = original_capacity or 1
        if new_capacity > baseline * 1.5:
            impact["changes"]["new_approvals_required"] = [
                "Enhanced Environmental Assessment",
                "MPCB Consent Renewal",
                "Factory Layout Re-approval",
            ]
            impact["changes"]["timeline_extension_days"] = 60
            impact["changes"]["cost_increase"] = 5000
        elif new_capacity > baseline * 1.2:
            impact["changes"]["modified_approvals"] = [
                "MPCB Consent Amendment",
                "Pollution Control Update",
            ]
            impact["changes"]["timeline_extension_days"] = 30
            impact["changes"]["cost_increase"] = 2000
        return impact

    def simulate_timeline_compression(self, original_project: dict, target_days: int) -> dict:
        original_timeline = original_project.get("estimated_approval_days", 180)
        if target_days < 0:
            target_days = 0
        compression_percent = ((original_timeline - target_days) / original_timeline * 100) if original_timeline else 0
        impact = {
            "scenario": "timeline_compression",
            "original_timeline_days": original_timeline,
            "target_timeline_days": target_days,
            "compression_percent": round(compression_percent, 2),
            "feasibility": self._assess_timeline_feasibility(original_project, target_days),
            "recommendations": [],
        }
        if compression_percent > 50:
            impact["feasibility"] = "low"
            impact["recommendations"] = [
                "Consider parallel approvals where possible",
                "Pre-prepare required documents before submission",
                "Use UdyogSetu SLA alerts for proactive follow-up",
            ]
        elif compression_percent > 30:
            impact["feasibility"] = "medium"
            impact["recommendations"] = [
                "Plan parallel processing of approvals",
                "Allocate dedicated applicant/consultant resources",
                "Track queries and inspections proactively",
            ]
        else:
            impact["feasibility"] = "high"
            impact["recommendations"] = [
                "Standard process should be workable under configured assumptions",
                "Maintain regular follow-ups",
            ]
        return impact

    # ------------------------------------------------------------------
    # Project-aware read-only simulator
    # ------------------------------------------------------------------
    async def simulate_project(
        self,
        project: Project,
        scenario_type: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict:
        if self.db is None:
            raise ValueError("A database session is required for project-aware simulation")

        normalized_type = (scenario_type or "").strip().lower()
        if normalized_type not in self.SUPPORTED_SCENARIOS:
            raise ValueError(f"Unknown scenario type: {normalized_type}")

        params = dict(parameters or {})
        baseline_data = self._project_payload(project)
        projected_data, scenario_meta = self._apply_scenario(baseline_data, normalized_type, params)
        baseline_obj = SimpleNamespace(**baseline_data)
        projected_obj = SimpleNamespace(**projected_data)

        rules = list((await self.db.execute(
            select(ApprovalRule).where(ApprovalRule.is_active.is_(True))
        )).scalars().all())
        existing_approvals = list((await self.db.execute(
            select(Approval).where(Approval.project_id == project.id)
        )).scalars().all())
        existing_status = {approval.name: self._status_value(approval.status) for approval in existing_approvals}

        approval_engine = ApprovalEngine(self.db)
        baseline_rules = [rule for rule in rules if approval_engine._evaluate_rule(rule, baseline_obj)]
        projected_rules = [rule for rule in rules if approval_engine._evaluate_rule(rule, projected_obj)]

        baseline_roadmap = self._projected_roadmap(baseline_rules, existing_status)
        projected_roadmap = self._projected_roadmap(projected_rules, existing_status)

        baseline_docs = self._required_documents(baseline_rules)
        projected_docs = self._required_documents(projected_rules)

        baseline_matches = await IncentiveMatcher(self.db).find_matching_schemes(self._incentive_data(baseline_data))
        projected_matches = await IncentiveMatcher(self.db).find_matching_schemes(self._incentive_data(projected_data))

        baseline_names = {item["name"] for item in baseline_matches}
        projected_names = {item["name"] for item in projected_matches}
        new_incentives = [item for item in projected_matches if item["name"] not in baseline_names]
        removed_incentives = [item for item in baseline_matches if item["name"] not in projected_names]

        baseline_rule_names = {rule.name for rule in baseline_rules}
        projected_rule_names = {rule.name for rule in projected_rules}
        added_rules = [rule for rule in projected_rules if rule.name not in baseline_rule_names]
        removed_rules = [rule for rule in baseline_rules if rule.name not in projected_rule_names]

        high_risk_before = sum(1 for rule in baseline_rules if (rule.risk_level or "").upper() == "HIGH")
        high_risk_after = sum(1 for rule in projected_rules if (rule.risk_level or "").upper() == "HIGH")
        risk_change = "INCREASED" if high_risk_after > high_risk_before else "DECREASED" if high_risk_after < high_risk_before else "UNCHANGED"
        risk_indicators: list[str] = []
        if baseline_data.get("hazardous_materials") != projected_data.get("hazardous_materials"):
            risk_indicators.append(
                "Hazardous-material handling flag changed; review the applicable safety and environmental controls."
            )
        if baseline_data.get("has_boiler") != projected_data.get("has_boiler"):
            risk_indicators.append(
                "Boiler configuration changed; review the applicable boiler safety workflow."
            )
        if high_risk_after != high_risk_before:
            risk_indicators.append(
                f"Configured high-risk approval count changes from {high_risk_before} to {high_risk_after}."
            )

        planning_signal = self._planning_signal(
            baseline_data,
            projected_data,
            normalized_type,
            params,
            baseline_roadmap["parallel_duration_days"],
        )
        recommendations = self._recommendations(
            normalized_type,
            added_rules,
            removed_rules,
            baseline_roadmap,
            projected_roadmap,
            projected_docs - baseline_docs,
            new_incentives,
            risk_change,
            planning_signal,
        )

        return {
            "scenario": {
                "type": normalized_type,
                "label": self.SUPPORTED_SCENARIOS[normalized_type]["label"],
                "parameters": params,
                "description": self.SUPPORTED_SCENARIOS[normalized_type]["description"],
                "meta": scenario_meta,
            },
            "baseline": {
                "project": self._public_project_data(baseline_data),
                "approval_count": len(baseline_rules),
                "mandatory_approval_count": sum(1 for rule in baseline_rules if rule.is_mandatory),
                "required_document_count": len(baseline_docs),
                "timeline": self._timeline_summary(baseline_roadmap),
                "high_risk_approval_count": high_risk_before,
                "incentives": self._incentive_summary(baseline_matches),
            },
            "projected": {
                "project": self._public_project_data(projected_data),
                "approval_count": len(projected_rules),
                "mandatory_approval_count": sum(1 for rule in projected_rules if rule.is_mandatory),
                "required_document_count": len(projected_docs),
                "timeline": self._timeline_summary(projected_roadmap),
                "high_risk_approval_count": high_risk_after,
                "incentives": self._incentive_summary(projected_matches),
            },
            "changes": {
                "approvals_added": [self._rule_payload(rule, "ADDED") for rule in added_rules],
                "approvals_removed": [self._rule_payload(rule, "REMOVED") for rule in removed_rules],
                "approvals_unchanged_count": len(baseline_rule_names & projected_rule_names),
                "required_documents_added": sorted(projected_docs - baseline_docs),
                "required_documents_removed": sorted(baseline_docs - projected_docs),
                "timeline_delta_days": projected_roadmap["parallel_duration_days"] - baseline_roadmap["parallel_duration_days"],
                "sequential_timeline_delta_days": projected_roadmap["sequential_duration_days"] - baseline_roadmap["sequential_duration_days"],
                "parallel_savings_delta_days": projected_roadmap["theoretical_time_saved_days"] - baseline_roadmap["theoretical_time_saved_days"],
                "high_risk_approval_delta": high_risk_after - high_risk_before,
                "risk_change": risk_change,
                "risk_indicators": risk_indicators,
                "new_incentives": new_incentives,
                "removed_incentives": removed_incentives,
                "incentive_score_changes": self._incentive_score_changes(baseline_matches, projected_matches),
            },
            "roadmap": {
                "baseline": baseline_roadmap,
                "projected": projected_roadmap,
            },
            "planning_signal": planning_signal,
            "recommendations": recommendations,
            "warnings": [
                "Scenario results are advisory planning estimates based on configured prototype rules/catalogues.",
                "They do not determine statutory applicability, government processing time, approval outcome, fees, or incentive entitlement.",
                "Location-specific and capacity-specific heuristics are planning signals unless directly supported by configured approval rules.",
            ],
        }

    def _apply_scenario(self, baseline: dict[str, Any], scenario_type: str, params: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        projected = dict(baseline)
        meta: dict[str, Any] = {}

        if scenario_type == "location_change":
            state = self._required_text(params, "new_state")
            district = self._required_text(params, "new_district")
            city = (str(params.get("new_city") or "").strip() or baseline.get("location_city"))
            projected.update({"location_state": state, "location_district": district, "location_city": city})
            meta = {"change": "location", "note": "Current approval rules do not all encode location; the location signal is shown separately."}
        elif scenario_type == "sector_upgrade":
            sector = self._required_text(params, "new_sector")
            industry = str(params.get("new_industry") or sector).strip()
            projected.update({"sector": sector, "industry": industry})
            meta = {"change": "sector", "note": "Configured approval rules and incentive catalogue drive the projected delta."}
        elif scenario_type == "investment_change":
            new_amount = self._number(params, "new_investment_amount", minimum=0)
            projected["investment_amount"] = new_amount
            meta = {"change": "investment", "delta": new_amount - float(baseline.get("investment_amount") or 0)}
        elif scenario_type == "capacity_expansion":
            current_capacity = self._number(params, "current_capacity", minimum=0.000001)
            new_capacity = self._number(params, "new_capacity", minimum=0.000001)
            if new_capacity < current_capacity:
                raise ValueError("new_capacity must be greater than or equal to current_capacity")
            projected["_scenario_capacity"] = new_capacity
            projected["water_consumption"] = float(baseline.get("water_consumption") or 0) * (new_capacity / current_capacity)
            projected["electricity_load"] = float(baseline.get("electricity_load") or 0) * (new_capacity / current_capacity)
            meta = {
                "change": "production_capacity",
                "current_capacity": current_capacity,
                "new_capacity": new_capacity,
                "increase_percent": round((new_capacity - current_capacity) / current_capacity * 100, 2),
            }
        elif scenario_type == "boiler_addition":
            has_boiler = self._bool(params, "has_boiler")
            projected["has_boiler"] = has_boiler
            meta = {"change": "boiler", "has_boiler": has_boiler}
        elif scenario_type == "hazardous_materials":
            hazardous = self._bool(params, "hazardous_materials")
            projected["hazardous_materials"] = hazardous
            meta = {"change": "hazardous_materials", "hazardous_materials": hazardous}
        elif scenario_type == "timeline_compression":
            target_days = self._number(params, "target_days", minimum=0)
            projected["_scenario_target_days"] = int(target_days)
            meta = {"change": "target_timeline", "target_days": int(target_days)}

        return projected, meta

    def _projected_roadmap(self, rules: list[ApprovalRule], existing_status: dict[str, str]) -> dict:
        rule_by_id = {str(rule.id): rule for rule in rules}
        rule_by_name = {rule.name: rule for rule in rules}
        nodes: list[dict] = []
        for rule in rules:
            raw_dependencies = rule.dependencies or []
            if isinstance(raw_dependencies, str):
                raw_dependencies = [raw_dependencies]
            dependencies = []
            for dependency in raw_dependencies:
                key = str(dependency)
                target = rule_by_id.get(key) or rule_by_name.get(key)
                if target:
                    dependencies.append(target.name)
            nodes.append({
                "id": str(rule.id),
                "label": rule.name,
                "department": rule.department,
                "days": max(0, int(rule.estimated_processing_days or 0)),
                "status": existing_status.get(rule.name, "NOT_STARTED"),
                "mandatory": bool(rule.is_mandatory),
                "dependencies": dependencies,
            })
        node_by_name = {node["label"]: node["id"] for node in nodes}
        edges = []
        index = 0
        for node in nodes:
            for dependency_name in node["dependencies"]:
                source = node_by_name.get(dependency_name)
                if source:
                    edges.append({"id": f"scenario-e{index}", "source": source, "target": node["id"]})
                    index += 1
        schedule = ApprovalGraphService._build_schedule(nodes, edges)
        parallel_duration = schedule["critical_path"]["duration_days"]
        sequential_duration = sum(node["days"] for node in nodes)
        parallel_savings = max(0, sequential_duration - parallel_duration)
        return {
            "approval_count": len(nodes),
            "parallel_duration_days": parallel_duration,
            "sequential_duration_days": sequential_duration,
            "theoretical_time_saved_days": parallel_savings,
            "critical_path_names": schedule["critical_path"]["names"],
            "schedule": schedule["items"],
            "parallel_groups": [
                {
                    "stage": stage,
                    "approval_count": len(ids),
                    "can_run_in_parallel": len(ids) > 1,
                    "approval_names": [next((node["label"] for node in nodes if node["id"] == node_id), node_id) for node_id in ids],
                }
                for stage, ids in schedule["levels"].items()
            ],
            "warnings": schedule["warnings"],
        }

    def _planning_signal(
        self,
        baseline: dict,
        projected: dict,
        scenario_type: str,
        params: dict,
        baseline_timeline_days: int,
    ) -> dict:
        if scenario_type == "location_change":
            return self.simulate_location_change(
                {"location": {"state": baseline.get("location_state"), "name": f"{baseline.get('location_district')}, {baseline.get('location_state')}"}},
                {"state": projected.get("location_state"), "name": f"{projected.get('location_district')}, {projected.get('location_state')}"},
            )
        if scenario_type == "sector_upgrade":
            return self.simulate_sector_upgrade({"sector": baseline.get("sector")}, projected.get("sector") or "")
        if scenario_type == "capacity_expansion":
            return self.simulate_capacity_expansion(
                {"capacity": params.get("current_capacity"), "sector": baseline.get("sector")},
                float(params.get("new_capacity")),
            )
        if scenario_type == "timeline_compression":
            return self.simulate_timeline_compression(
                {"estimated_approval_days": baseline_timeline_days},
                int(params.get("target_days")),
            )
        if scenario_type in {"boiler_addition", "hazardous_materials"}:
            return {
                "scenario": scenario_type,
                "type": "approval_rule_projection",
                "note": "This scenario is assessed primarily through the configured approval rules and risk indicators.",
            }
        if scenario_type == "investment_change":
            return {
                "scenario": scenario_type,
                "type": "catalog_projection",
                "note": "Investment changes are reflected through configured approval conditions and incentive catalogue ranges.",
            }
        return {}

    @staticmethod
    def _recommendations(
        scenario_type: str,
        added_rules: list[ApprovalRule],
        removed_rules: list[ApprovalRule],
        baseline_roadmap: dict,
        projected_roadmap: dict,
        new_docs: set[str],
        new_incentives: list[dict],
        risk_change: str,
        planning_signal: dict,
    ) -> list[str]:
        recommendations: list[str] = []
        if added_rules:
            recommendations.append(f"Review {len(added_rules)} newly applicable approval rule(s) before acting on the scenario.")
        if removed_rules:
            recommendations.append(f"Confirm {len(removed_rules)} approval rule(s) would no longer match the configured project profile.")
        if new_docs:
            recommendations.append(f"Plan for {len(new_docs)} additional document type(s): {', '.join(sorted(new_docs)[:4])}.")
        timeline_delta = projected_roadmap["parallel_duration_days"] - baseline_roadmap["parallel_duration_days"]
        if timeline_delta > 0:
            recommendations.append(f"The projected critical-path estimate increases by {timeline_delta} day(s); review the new critical-path approvals.")
        elif timeline_delta < 0:
            recommendations.append(f"The projected critical-path estimate decreases by {abs(timeline_delta)} day(s) under the configured dependencies.")
        if risk_change == "INCREASED":
            recommendations.append("Additional high-risk approval signals appear in the projected configuration; review safeguards before proceeding.")
        if new_incentives:
            recommendations.append(f"Re-check {len(new_incentives)} newly matched incentive catalogue item(s) before relying on their benefits.")
        if scenario_type == "timeline_compression":
            recommendations.extend(planning_signal.get("recommendations", [])[:2])
        if not recommendations:
            recommendations.append("No material change was detected by the configured prototype rules; confirm assumptions before making a real project change.")
        return list(dict.fromkeys(recommendations))

    @staticmethod
    def _timeline_summary(roadmap: dict) -> dict:
        return {
            "parallel_duration_days": roadmap["parallel_duration_days"],
            "sequential_duration_days": roadmap["sequential_duration_days"],
            "theoretical_time_saved_days": roadmap["theoretical_time_saved_days"],
            "critical_path_names": roadmap["critical_path_names"],
        }

    @staticmethod
    def _required_documents(rules: list[ApprovalRule]) -> set[str]:
        result: set[str] = set()
        for rule in rules:
            for doc in rule.required_documents or []:
                result.add(str(doc))
        return result

    @staticmethod
    def _incentive_data(project_data: dict) -> dict:
        return {
            "industry": project_data.get("industry"),
            "sector": project_data.get("sector"),
            "state": project_data.get("location_state"),
            "investment_amount": project_data.get("investment_amount"),
            "employees": project_data.get("employees"),
            "business_type": project_data.get("business_type"),
        }

    @staticmethod
    def _incentive_summary(matches: list[dict]) -> list[dict]:
        return [
            {
                "id": item["id"],
                "name": item["name"],
                "match_score": item.get("match_score", 0),
                "match_reason": item.get("match_reason"),
            }
            for item in matches[:8]
        ]

    @staticmethod
    def _incentive_score_changes(before: list[dict], after: list[dict]) -> list[dict]:
        before_map = {item["id"]: item for item in before}
        changes = []
        for item in after:
            old = before_map.get(item["id"])
            if old and old.get("match_score") != item.get("match_score"):
                changes.append({
                    "id": item["id"],
                    "name": item["name"],
                    "before": old.get("match_score", 0),
                    "after": item.get("match_score", 0),
                    "delta": item.get("match_score", 0) - old.get("match_score", 0),
                })
        return changes[:10]

    @staticmethod
    def _rule_payload(rule: ApprovalRule, change: str) -> dict:
        return {
            "name": rule.name,
            "department": rule.department,
            "mandatory": bool(rule.is_mandatory),
            "risk_level": rule.risk_level,
            "estimated_processing_days": rule.estimated_processing_days or 0,
            "required_documents": list(rule.required_documents or []),
            "source": rule.source,
            "source_url": rule.source_url,
            "change": change,
        }

    @staticmethod
    def _project_payload(project: Project) -> dict[str, Any]:
        return {
            "name": project.name,
            "company_name": project.company_name,
            "business_type": project.business_type,
            "industry": project.industry,
            "sector": project.sector,
            "project_stage": project.project_stage,
            "investment_amount": project.investment_amount,
            "location_state": project.location_state,
            "location_district": project.location_district,
            "location_city": project.location_city,
            "employees": project.employees,
            "production_type": project.production_type,
            "hazardous_materials": project.hazardous_materials,
            "has_boiler": project.has_boiler,
            "electricity_load": project.electricity_load,
            "water_consumption": project.water_consumption,
            "pollution_potential": project.pollution_potential,
            "building_type": project.building_type,
            "is_new": project.is_new,
            "description": project.description,
        }

    @staticmethod
    def _public_project_data(data: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in data.items() if not key.startswith("_")}

    @staticmethod
    def _status_value(value: Any) -> str:
        return value.value if hasattr(value, "value") else str(value)

    @staticmethod
    def _required_text(params: dict, key: str) -> str:
        value = str(params.get(key) or "").strip()
        if not value:
            raise ValueError(f"{key} is required")
        return value

    @staticmethod
    def _number(params: dict, key: str, minimum: float | None = None) -> float:
        value = params.get(key)
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{key} must be numeric") from None
        if minimum is not None and number < minimum:
            raise ValueError(f"{key} must be at least {minimum}")
        return number

    @staticmethod
    def _bool(params: dict, key: str) -> bool:
        value = params.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            if value.strip().lower() in {"true", "1", "yes", "on"}:
                return True
            if value.strip().lower() in {"false", "0", "no", "off"}:
                return False
        raise ValueError(f"{key} must be a boolean")

    def _get_location_approvals(self, location) -> list:
        if isinstance(location, dict):
            state = (location.get("state") or "").upper()
        elif isinstance(location, str):
            state = location.upper()
        else:
            state = ""
        location_approvals = {
            "MAHARASHTRA": ["MPCB Consent", "MIDC Clearance", "Municipal Approval"],
            "GUJARAT": ["GPCB Consent", "GIDC Clearance"],
            "TAMIL_NADU": ["TNPCB Consent", "SIPCOT Clearance"],
        }
        return location_approvals.get(state, ["General Industrial Approval"])

    def _get_sector_approvals(self, sector: str) -> list:
        sector_lower = (sector or "").lower()
        approvals = {
            "textile": ["Factory License", "MPCB Consent", "DGFT License", "Labour License"],
            "chemicals": ["Factory License", "MPCB Consent", "SPCB Clearance", "Fire Permission"],
            "manufacturing": ["Factory License", "Boiler Registration", "Labour License"],
            "food": ["Food License", "Health Clearance", "Municipal Approval"],
        }
        for key, value in approvals.items():
            if key in sector_lower:
                return value
        return ["Factory License", "Labour License"]

    def _get_pollution_category(self, sector: str) -> str:
        sector_lower = (sector or "").lower()
        if any(word in sector_lower for word in ["chemical", "steel", "refinery", "textile"]):
            return "RED"
        if any(word in sector_lower for word in ["pharmaceutical", "food", "beverage"]):
            return "ORANGE"
        return "GREEN"

    def _assess_timeline_feasibility(self, project: dict, target_days: int) -> str:
        original = project.get("estimated_approval_days", 180)
        if target_days >= original * 0.8:
            return "high"
        if target_days >= original * 0.5:
            return "medium"
        return "low"
