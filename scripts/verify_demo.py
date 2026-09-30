"""Verify that the SIH demo dataset is ready for presentation.

Usage:
    python scripts/verify_demo.py

Returns exit code 0 only when every read-only demo readiness check passes.
"""
from __future__ import annotations

import asyncio
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))


async def verify() -> int:
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models import User
    from app.services.demo_readiness import DemoReadinessService

    email = os.environ.get("DEMO_EMAIL", "demo@abctextiles.in")
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == email).limit(1))).scalar_one_or_none()
        if user is None:
            print(f"Demo user not found: {email}")
            return 1
        report = await DemoReadinessService(db).inspect(user.id)

    print("SIH DEMO READINESS")
    print("=" * 60)
    print(f"Score: {report['score']}% ({report['passed']}/{report['total']})")
    for check in report["checks"]:
        marker = "PASS" if check["ok"] else "FAIL"
        print(f"[{marker}] {check['label']}: {check['detail']}")
    print(report["disclaimer"])
    return 0 if report["ready"] else 1


def main() -> int:
    return asyncio.run(verify())


if __name__ == "__main__":
    raise SystemExit(main())
