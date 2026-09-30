"""Step 16 regression tests for the project-aware scenario simulator."""

import asyncio
import uuid

from app.models import ApprovalRule, Project, Scheme, User, UserRole
from app.services.scenario_simulator import ScenarioSimulator


def _user_id() -> uuid.UUID:
    return uuid.uuid4()


def _project(user_id: uuid.UUID, **overrides) -> Project:
    values = {
        "user_id": user_id,
        "name": "Scenario Factory",
        "company_name": "Scenario Industries Pvt Ltd",
        "business_type": "manufacturing",
        "industry": "Manufacturing",
        "sector": "Manufacturing",
        "project_stage": "feasibility",
        "investment_amount": 5_000_000,
        "location_state": "Maharashtra",
        "location_district": "Pune",
        "location_city": "Pune",
        "employees": 5,
        "production_type": "continuous",
        "hazardous_materials": False,
        "has_boiler": False,
        "electricity_load": 100.0,
        "water_consumption": 500.0,
        "pollution_potential": "low",
        "building_type": "industrial",
        "is_new": True,
    }
    values.update(overrides)
    return Project(**values)


def _rule(name, field, operator, value, *, days, risk="MEDIUM", documents=None, dependency=None, mandatory=True):
    conditions = {"type": "COMPARISON", "field": field, "operator": operator, "value": value}
    return ApprovalRule(
        name=name,
        department=name + " Department",
        sector="All",
        conditions=conditions,
        is_mandatory=mandatory,
        required_documents=documents or [],
        dependencies=[dependency] if dependency else [],
        estimated_processing_days=days,
        risk_level=risk,
        is_active=True,
    )


async def _seed_rules(session):
    session.add_all([
        _rule("Factory License", "employees", "greater_than", 9, days=30, documents=["Factory Plan"]),
        _rule("Boiler Registration", "has_boiler", "equals", True, days=15, risk="HIGH", documents=["Boiler Specification"], dependency="Factory License"),
        _rule("Fire No Objection Certificate", "hazardous_materials", "equals", True, days=20, documents=["Fire Safety Plan"]),
        _rule("GST Registration", "employees", "greater_than", 0, days=7, risk="LOW", documents=["PAN Card"]),
    ])
    session.add(Scheme(
        name="MSME Subsidy Scheme",
        department="MSME",
        sector="Manufacturing",
        location="Maharashtra",
        min_investment=1_000_000,
        max_investment=50_000_000,
        eligible_entity="MSME",
        employee_requirement=5,
        benefits=["25% subsidy on capital investment"],
        required_documents=["Company Registration"],
        is_active=True,
    ))
    session.add(Scheme(
        name="Packaged Scheme of Incentives (PSI)",
        department="MIDC",
        sector="All",
        location="Maharashtra",
        min_investment=50_000_000,
        max_investment=5_000_000_000,
        eligible_entity="Large Industry",
        employee_requirement=100,
        benefits=["30% capital subsidy"],
        required_documents=["Project Report"],
        is_active=True,
    ))
    await session.commit()


async def _run(db_session, scenario_type, params, **project_overrides):
    user_id = _user_id()
    user = User(id=user_id, email=f"scenario-{user_id.hex[:8]}@example.com", name="Scenario User", phone="9876543210", password_hash="x", role=UserRole.ENTREPRENEUR)
    project = _project(user_id, **project_overrides)
    db_session.add_all([user, project])
    await db_session.commit()
    await db_session.refresh(project)
    await _seed_rules(db_session)
    return await ScenarioSimulator(db_session).simulate_project(project, scenario_type, params)


class TestProjectScenarioSimulator:
    async def test_boiler_addition_uses_actual_rules_and_shows_delta(self, db_session):
        result = await _run(db_session, "boiler_addition", {"has_boiler": True})
        added = {item["name"] for item in result["changes"]["approvals_added"]}
        assert "Boiler Registration" in added
        assert result["changes"]["high_risk_approval_delta"] == 1
        assert "Boiler Specification" in result["changes"]["required_documents_added"]
        assert result["projected"]["timeline"]["parallel_duration_days"] >= result["baseline"]["timeline"]["parallel_duration_days"]

    async def test_hazardous_materials_can_add_fire_requirement(self, db_session):
        result = await _run(db_session, "hazardous_materials", {"hazardous_materials": True})
        added = {item["name"] for item in result["changes"]["approvals_added"]}
        assert "Fire No Objection Certificate" in added
        assert "Fire Safety Plan" in result["changes"]["required_documents_added"]

    async def test_investment_change_updates_incentive_scores(self, db_session):
        result = await _run(db_session, "investment_change", {"new_investment_amount": 50_000_000})
        changed = {item["name"] for item in result["changes"]["incentive_score_changes"]}
        assert changed, "Investment change should alter at least one configured incentive score"
        assert "Packaged Scheme of Incentives (PSI)" in changed
        assert result["projected"]["project"]["investment_amount"] == 50_000_000

    async def test_location_change_reports_rule_and_planning_layers(self, db_session):
        result = await _run(
            db_session,
            "location_change",
            {"new_state": "Gujarat", "new_district": "Ahmedabad", "new_city": "Ahmedabad"},
        )
        assert result["projected"]["project"]["location_state"] == "Gujarat"
        assert result["planning_signal"]["scenario"] == "location_change"
        # Current configured approval rules do not encode location; the simulator must not invent rule changes.
        assert result["changes"]["approvals_added"] == []

    async def test_capacity_expansion_requires_valid_order(self, db_session):
        result = await _run(
            db_session,
            "capacity_expansion",
            {"current_capacity": 100, "new_capacity": 250},
        )
        assert result["scenario"]["meta"]["increase_percent"] == 150.0
        assert result["planning_signal"]["changes"]["timeline_extension_days"] == 60

    async def test_timeline_compression_uses_actual_baseline_duration(self, db_session):
        result = await _run(db_session, "timeline_compression", {"target_days": 2})
        assert result["planning_signal"]["scenario"] == "timeline_compression"
        assert result["planning_signal"]["original_timeline_days"] == result["baseline"]["timeline"]["parallel_duration_days"]
        assert result["planning_signal"]["feasibility"] == "low"

    async def test_invalid_parameters_are_rejected(self, db_session):
        user_id = _user_id()
        project = _project(user_id)
        simulator = ScenarioSimulator(db_session)
        for scenario_type, params in [
            ("investment_change", {"new_investment_amount": -1}),
            ("capacity_expansion", {"current_capacity": 100, "new_capacity": 50}),
            ("location_change", {"new_state": "", "new_district": "Pune"}),
            ("boiler_addition", {"has_boiler": "not-a-bool"}),
        ]:
            try:
                await simulator.simulate_project(project, scenario_type, params)
            except ValueError:
                continue
            raise AssertionError(f"Expected ValueError for {scenario_type}")
