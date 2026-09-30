"""Unit/integration tests for the core service and rules modules."""

import types
import uuid

from app.models import ApprovalRule, Document, DocumentStatus, Project
from app.rules.approval_engine import ApprovalEngine
from app.services.compliance_tracker import ComplianceTracker
from app.services.document_processor import DocumentProcessorService
from app.services.incentive_matcher import IncentiveMatcher
from app.services.scenario_simulator import ScenarioSimulator


def _dummy_project():
    return types.SimpleNamespace()


class TestApprovalEngineConditions:
    """Decision-logic unit tests (no DB required)."""

    def _engine(self):
        return ApprovalEngine(db=None)

    def test_and_condition(self):
        engine = self._engine()
        condition = {
            "type": "AND",
            "conditions": [
                {"type": "COMPARISON", "field": "sector", "operator": "equals", "value": "Textile"},
                {"type": "COMPARISON", "field": "capacity", "operator": "greater_than", "value": 50},
            ],
        }
        assert engine._evaluate_conditions(
            condition, types.SimpleNamespace(sector="Textile", capacity=100)
        ) is True
        assert engine._evaluate_conditions(
            condition, types.SimpleNamespace(sector="Food", capacity=100)
        ) is False

    def test_or_condition(self):
        engine = self._engine()
        condition = {
            "type": "OR",
            "conditions": [
                {"type": "COMPARISON", "field": "sector", "operator": "equals", "value": "Textile"},
                {"type": "COMPARISON", "field": "sector", "operator": "equals", "value": "Chemical"},
            ],
        }
        assert engine._evaluate_conditions(
            condition, types.SimpleNamespace(sector="Textile")
        ) is True
        assert engine._evaluate_conditions(
            condition, types.SimpleNamespace(sector="Chemical")
        ) is True
        assert engine._evaluate_conditions(
            condition, types.SimpleNamespace(sector="Food")
        ) is False

    def test_not_condition(self):
        engine = self._engine()
        condition = {
            "type": "NOT",
            "condition": {"type": "COMPARISON", "field": "sector", "operator": "equals", "value": "Food"},
        }
        assert engine._evaluate_conditions(
            condition, types.SimpleNamespace(sector="Textile")
        ) is True
        assert engine._evaluate_conditions(
            condition, types.SimpleNamespace(sector="Food")
        ) is False

    def test_equals_operator(self):
        engine = self._engine()
        condition = {"type": "COMPARISON", "field": "sector", "operator": "equals", "value": "Textile"}
        assert engine._evaluate_comparison(condition, types.SimpleNamespace(sector="Textile")) is True
        assert engine._evaluate_comparison(condition, types.SimpleNamespace(sector="Food")) is False

    def test_greater_than_operator(self):
        engine = self._engine()
        condition = {"type": "COMPARISON", "field": "capacity", "operator": "greater_than", "value": 100}
        assert engine._evaluate_comparison(condition, types.SimpleNamespace(capacity=200)) is True
        assert engine._evaluate_comparison(condition, types.SimpleNamespace(capacity=50)) is False
        assert engine._evaluate_comparison(condition, types.SimpleNamespace(capacity=100)) is False

    def test_contains_operator(self):
        engine = self._engine()
        condition = {"type": "COMPARISON", "field": "description", "operator": "contains", "value": "pollution"}
        assert engine._evaluate_comparison(
            condition, types.SimpleNamespace(description="high pollution potential")
        ) is True
        assert engine._evaluate_comparison(
            condition, types.SimpleNamespace(description="low impact")
        ) is False

    def test_in_operator(self):
        engine = self._engine()
        condition = {"type": "COMPARISON", "field": "state", "operator": "in", "value": ["Maharashtra", "Gujarat"]}
        assert engine._evaluate_comparison(condition, types.SimpleNamespace(state="Maharashtra")) is True
        assert engine._evaluate_comparison(condition, types.SimpleNamespace(state="Tamil Nadu")) is False

    def test_unknown_operator_returns_false(self):
        engine = self._engine()
        condition = {"type": "COMPARISON", "field": "sector", "operator": "not_a_thing", "value": "Textile"}
        assert engine._evaluate_comparison(condition, types.SimpleNamespace(sector="Textile")) is False


class TestApprovalEngineDetermination:
    """DB-backed tests for the rule evaluation flow."""

    @staticmethod
    def _insert_project(session) -> Project:
        project = Project(
            user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            name="Test Project",
            company_name="Test Corp",
            sector="Textile",
            location_state="Maharashtra",
        )
        session.add(project)
        return project

    async def test_determines_applicable_approvals(self, db_session):
        project = self._insert_project(db_session)
        await db_session.commit()
        await db_session.refresh(project)

        db_session.add(
            ApprovalRule(
                name="MPCB Consent to Establish",
                department="MPCB",
                sector="Textile",
                conditions={
                    "type": "COMPARISON",
                    "field": "sector",
                    "operator": "equals",
                    "value": "Textile",
                },
                is_mandatory=True,
                is_active=True,
            )
        )
        await db_session.commit()

        engine = ApprovalEngine(db_session)
        approvals = await engine.determine_approvals(project.id)

        assert len(approvals) == 1
        assert approvals[0]["name"] == "MPCB Consent to Establish"
        assert approvals[0]["department"] == "MPCB"
        assert approvals[0]["is_mandatory"] is True
        assert "id" in approvals[0]

    async def test_determine_approvals_no_rules(self, db_session):
        project = self._insert_project(db_session)
        await db_session.commit()
        await db_session.refresh(project)

        engine = ApprovalEngine(db_session)
        approvals = await engine.determine_approvals(project.id)

        assert approvals == []

    async def test_determine_approvals_missing_project(self, db_session):
        engine = ApprovalEngine(db_session)
        approvals = await engine.determine_approvals(uuid.uuid4())
        assert approvals == []

    async def test_non_matching_rule_excluded(self, db_session):
        project = self._insert_project(db_session)
        await db_session.commit()
        await db_session.refresh(project)

        db_session.add(
            ApprovalRule(
                name="Fishery License",
                department="Fisheries",
                sector="Fishery",
                conditions={
                    "type": "COMPARISON",
                    "field": "sector",
                    "operator": "equals",
                    "value": "Fishery",
                },
                is_active=True,
            )
        )
        await db_session.commit()

        engine = ApprovalEngine(db_session)
        approvals = await engine.determine_approvals(project.id)

        assert approvals == []


class TestDocumentProcessor:
    async def test_validate_missing_document(self, db_session):
        service = DocumentProcessorService(db_session)
        result = await service.validate_document(uuid.uuid4())
        assert result == {"error": "Document not found"}

    async def test_get_missing_document_returns_none(self, db_session):
        service = DocumentProcessorService(db_session)
        result = await service.get_document(uuid.uuid4())
        assert result is None

    async def test_get_and_validate_document(self, db_session):
        project = Project(
            user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            name="P",
            company_name="C",
            sector="Textile",
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        document = Document(
            project_id=project.id,
            file_name="factory-license.pdf",
            file_path="/tmp/factory-license.pdf",
            file_type="application/pdf",
            file_size=1234,
            status=DocumentStatus.UPLOADED,
            extracted_fields={"registration_id": "12345"},
        )
        db_session.add(document)
        await db_session.commit()
        await db_session.refresh(document)

        service = DocumentProcessorService(db_session)
        fetched = await service.get_document(document.id)
        assert fetched is not None
        assert fetched.file_name == "factory-license.pdf"

        validation = await service.validate_document(document.id)
        assert validation["document_id"] == str(document.id)
        assert validation["extracted_fields"] == {"registration_id": "12345"}


class TestScenarioSimulator:
    def test_location_change_impacts_timeline(self):
        simulator = ScenarioSimulator()
        impact = simulator.simulate_location_change(
            {"location": {"state": "MAHARASHTRA", "name": "Pune"}, "sector": "Manufacturing"},
            {"name": "Ahmedabad, Gujarat", "state": "Gujarat"},
        )
        total_change = (
            len(impact["changes"]["approvals_added"])
            - len(impact["changes"]["approvals_removed"])
        )
        assert impact["changes"]["timeline_change_days"] != 0 or total_change == 0
        assert impact["changes"]["timeline_change_days"] == total_change * 30

    def test_capacity_expansion_requires_additional_approvals(self):
        simulator = ScenarioSimulator()
        result = simulator.simulate_capacity_expansion(
            {"capacity": 100, "sector": "Manufacturing"},
            250,
        )
        assert result["capacity_increase_percent"] == 150.0
        assert len(result["changes"]["new_approvals_required"]) > 0
        assert result["changes"]["timeline_extension_days"] > 0

    def test_timeline_compression_feasibility(self):
        simulator = ScenarioSimulator()

        result1 = simulator.simulate_timeline_compression(
            {"estimated_approval_days": 180},
            150,
        )
        assert result1["feasibility"] in ["low", "medium", "high"]

        result2 = simulator.simulate_timeline_compression(
            {"estimated_approval_days": 180},
            30,
        )
        assert result2["feasibility"] == "low"

    def test_sector_upgrade(self):
        simulator = ScenarioSimulator()
        result = simulator.simulate_sector_upgrade(
            {"sector": "manufacturing", "location": {"state": "MAHARASHTRA"}},
            "textile",
        )
        assert result["scenario"] == "sector_upgrade"
        assert result["new_sector"] == "textile"
        assert len(result["changes"]["approvals_required"]) > 0


class TestIncentiveMatcher:
    async def test_no_matches_without_schemes(self, db_session):
        matcher = IncentiveMatcher(db_session)
        matches = await matcher.find_matching_schemes(
            {
                "sector": "Textile",
                "state": "Maharashtra",
                "investment_amount": 1000000,
                "employees": 50,
            }
        )
        assert matches == []


class TestComplianceTracker:
    async def test_missing_project_score_zero(self, db_session):
        tracker = ComplianceTracker(db_session)
        result = await tracker.get_compliance_score(str(uuid.uuid4()))
        assert result == {"score": 0}

    async def test_project_score_components_when_no_approvals(self, db_session):
        project = Project(
            user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            name="P",
            company_name="C",
            sector="Textile",
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        tracker = ComplianceTracker(db_session)
        result = await tracker.get_compliance_score(str(project.id))

        assert result["score"] == 0
        assert "components" in result
        assert result["components"]["approval_status"] == 0