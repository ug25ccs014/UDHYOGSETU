"""Tests for the knowledge graph builder (spec §31)."""

from app.models import (
    Approval,
    ComplianceItem,
    Document,
    Project,
    User,
    UserRole,
)
from app.services.knowledge_graph import KnowledgeGraphService


async def _user(db, email="kg@example.com"):
    u = User(
        email=email,
        name="KG Tester",
        phone="9999000011",
        password_hash="x" * 60,
        role=UserRole.ENTREPRENEUR,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


async def test_project_approval_knowledge_graph(db_session):
    u = await _user(db_session)
    project = Project(
        user_id=u.id,
        name="ABC Textiles",
        company_name="ABC Textiles Pvt Ltd",
        industry="textiles",
        sector="textiles",
        location_district="Nashik",
        investment_amount=5000000,
        employees=50,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    approval = Approval(
        project_id=project.id,
        name="Consent to Establish",
        department="mpcb",
        sector="textiles",
    )
    db_session.add(approval)
    doc = Document(
        project_id=project.id,
        file_name="consent.pdf",
        file_path="/tmp/consent.pdf",
        file_type="pdf",
    )
    db_session.add(doc)
    comp = ComplianceItem(
        project_id=project.id,
        category="pollution",
        requirement="Submit environmental audit",
    )
    db_session.add(comp)
    await db_session.commit()

    graph = await KnowledgeGraphService(db_session).build_graph(project.id)

    assert graph["stats"]["approvals"] == 1
    # At least one PROJECT_REQUIRES_APPROVAL relationship.
    assert any(r["type"] == "PROJECT_REQUIRES_APPROVAL" for r in graph["relationships"])
    # The approval node is present.
    ids = [n["id"] for n in graph["nodes"]]
    assert any(nid.startswith("approval:") for nid in ids)
    # Documents linked as nodes.
    assert any(nid.startswith("doc:") for nid in ids)
    # Compliance node present.
    assert any(nid.startswith("comp:") for nid in ids)


async def test_missing_project_returns_empty(db_session):
    import uuid
    graph = await KnowledgeGraphService(db_session).build_graph(uuid.uuid4())
    assert graph["nodes"] == []
    assert graph["stats"] == {}
