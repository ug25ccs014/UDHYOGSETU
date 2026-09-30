"""Tests for the approval dependency graph + critical-path analysis."""

import uuid

import pytest

from app.models import Approval, ApprovalRule, Project, User


@pytest.fixture
async def project_with_rules(db_session):
    user = User(
        email=f"graph-{uuid.uuid4().hex[:8]}@example.com",
        name="Graph User",
        phone="9876501111",
        role="ENTREPRENEUR",
    )
    user.password_hash = "x"
    db_session.add(user)
    await db_session.flush()

    project = Project(
        user_id=user.id,
        name="Graph Project",
        company_name="Graph Corp",
    )
    db_session.add(project)
    await db_session.flush()

    return user, project


@pytest.mark.asyncio
async def test_graph_builds_nodes_and_reports_duration(db_session, project_with_rules):
    from app.services.approval_graph import ApprovalGraphService

    _user, project = project_with_rules

    r1 = ApprovalRule(
        id=uuid.UUID("10000000-0000-0000-0000-000000000001"),
        name="Consent to Establish",
        department="MPCB",
        conditions={"type": "COMPARISON", "field": "x", "operator": "equals", "value": 1},
        dependencies=[],
        estimated_processing_days=60,
    )
    r2 = ApprovalRule(
        id=uuid.UUID("10000000-0000-0000-0000-000000000002"),
        name="Consent to Operate",
        department="MPCB",
        conditions={"type": "COMPARISON", "field": "x", "operator": "equals", "value": 1},
        dependencies=["10000000-0000-0000-0000-000000000001"],
        estimated_processing_days=45,
    )
    db_session.add_all([r1, r2])
    await db_session.flush()

    a1 = Approval(project_id=project.id, name="Consent to Establish", department="MPCB", estimated_processing_days=60)
    a2 = Approval(project_id=project.id, name="Consent to Operate", department="MPCB", estimated_processing_days=45)
    db_session.add_all([a1, a2])
    await db_session.commit()

    svc = ApprovalGraphService(db_session)
    graph = await svc.build_graph(project.id)

    assert len(graph["nodes"]) == 2
    # edge from rule1 -> rule2 exists
    assert len(graph["edges"]) == 1
    assert graph["critical_path"]["duration_days"] == 60 + 45
    assert graph["critical_path"]["approvals"]


@pytest.mark.asyncio
async def test_graph_handles_no_approvals(db_session, project_with_rules):
    from app.services.approval_graph import ApprovalGraphService

    _user, project = project_with_rules
    await db_session.commit()

    svc = ApprovalGraphService(db_session)
    graph = await svc.build_graph(project.id)
    assert graph["nodes"] == []
    assert graph["edges"] == []
    assert graph["critical_path"]["duration_days"] == 0

@pytest.mark.asyncio
async def test_graph_reports_parallel_groups_and_theoretical_savings(db_session, project_with_rules):
    from app.services.approval_graph import ApprovalGraphService

    _user, project = project_with_rules

    r1 = ApprovalRule(
        id=uuid.UUID("10000000-0000-0000-0000-000000000011"),
        name="Factory License",
        department="Factory",
        conditions={"type": "COMPARISON", "field": "x", "operator": "equals", "value": 1},
        dependencies=[],
        estimated_processing_days=30,
    )
    r2 = ApprovalRule(
        id=uuid.UUID("10000000-0000-0000-0000-000000000012"),
        name="Fire NOC",
        department="Fire",
        conditions={"type": "COMPARISON", "field": "x", "operator": "equals", "value": 1},
        dependencies=[],
        estimated_processing_days=10,
    )
    r3 = ApprovalRule(
        id=uuid.UUID("10000000-0000-0000-0000-000000000013"),
        name="Boiler Registration",
        department="Boiler",
        conditions={"type": "COMPARISON", "field": "x", "operator": "equals", "value": 1},
        dependencies=[str(r1.id)],
        estimated_processing_days=20,
    )
    db_session.add_all([r1, r2, r3])
    await db_session.flush()

    db_session.add_all(
        [
            Approval(project_id=project.id, name=r1.name, department=r1.department, estimated_processing_days=30),
            Approval(project_id=project.id, name=r2.name, department=r2.department, estimated_processing_days=10),
            Approval(project_id=project.id, name=r3.name, department=r3.department, estimated_processing_days=20),
        ]
    )
    await db_session.commit()

    graph = await ApprovalGraphService(db_session).build_graph(project.id)

    assert graph["summary"]["sequential_duration_days"] == 60
    assert graph["summary"]["parallel_duration_days"] == 50
    assert graph["summary"]["theoretical_time_saved_days"] == 10
    assert graph["summary"]["parallel_group_count"] == 1
    assert graph["parallel_groups"][0]["approval_count"] == 2
    assert graph["critical_path"]["duration_days"] == 50


@pytest.mark.asyncio
async def test_graph_resolves_rule_name_dependencies(db_session, project_with_rules):
    from app.services.approval_graph import ApprovalGraphService

    _user, project = project_with_rules

    r1 = ApprovalRule(
        name="Site Approval",
        department="Planning",
        conditions={"type": "COMPARISON", "field": "x", "operator": "equals", "value": 1},
        dependencies=[],
        estimated_processing_days=10,
    )
    r2 = ApprovalRule(
        name="Factory License",
        department="Factory",
        conditions={"type": "COMPARISON", "field": "x", "operator": "equals", "value": 1},
        dependencies=["Site Approval"],
        estimated_processing_days=30,
    )
    db_session.add_all([r1, r2])
    await db_session.flush()
    db_session.add_all(
        [
            Approval(project_id=project.id, name=r1.name, department=r1.department, estimated_processing_days=10),
            Approval(project_id=project.id, name=r2.name, department=r2.department, estimated_processing_days=30),
        ]
    )
    await db_session.commit()

    graph = await ApprovalGraphService(db_session).build_graph(project.id)
    assert len(graph["edges"]) == 1
    assert graph["edges"][0]["dependency"] == "Site Approval"
