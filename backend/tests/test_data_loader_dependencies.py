"""Tests for stable approval-rule dependency normalization."""

import json
import uuid

import pytest
from sqlalchemy import select

from app.models import ApprovalRule, User


@pytest.mark.asyncio
async def test_load_approval_rules_normalizes_catalog_dependency_ids(db_session, tmp_path):
    from app.services.data_loader import RuleLoadingService

    # Simulate a rule already persisted by an older seed that kept the external ID.
    existing = ApprovalRule(
        id=uuid.uuid4(),
        name="Factory License",
        department="Factory",
        conditions={"type": "COMPARISON", "field": "employees", "operator": "greater_than", "value": 9},
        dependencies=["rule_legacy"],
    )
    db_session.add(existing)
    await db_session.commit()

    payload = [
        {
            "id": "rule_002",
            "name": "Factory License",
            "department": "Factory",
            "conditions": existing.conditions,
            "dependencies": [],
        },
        {
            "id": "rule_003",
            "name": "Boiler Registration",
            "department": "Boiler",
            "conditions": existing.conditions,
            "dependencies": ["rule_002"],
        },
    ]
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    await RuleLoadingService(db_session).load_approval_rules(str(path))

    rules = {
        rule.name: rule
        for rule in (await db_session.execute(select(ApprovalRule))).scalars().all()
    }
    assert rules["Factory License"].dependencies == []
    assert rules["Boiler Registration"].dependencies == ["Factory License"]
