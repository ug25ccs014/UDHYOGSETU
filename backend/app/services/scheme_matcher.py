"""Backward-compatible wrapper around the canonical incentive matcher.

Step 15 establishes ``IncentiveMatcher`` as the single matching engine. This
class remains for older callers/imports but delegates to the canonical service
instead of maintaining a second set of matching rules.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import SchemeMatcher as SchemeMatcherInput
from app.services.incentive_matcher import IncentiveMatcher


class SchemeMatcher:
    """Compatibility facade for the legacy scheme matcher API."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._matcher = IncentiveMatcher(db)

    async def find_matching_schemes(self, matcher: SchemeMatcherInput) -> list[dict]:
        project_data = {
            "industry": matcher.industry,
            "sector": matcher.industry,
            "state": matcher.location,
            "location": matcher.location,
            "investment_amount": matcher.investment,
            "employees": matcher.employees,
            "business_type": matcher.business_type,
        }
        return await self._matcher.find_matching_schemes(project_data)

    async def get_scheme(self, scheme_id):
        details = await self._matcher.get_scheme_details(str(scheme_id))
        if not details:
            return None
        return {"id": details.get("scheme_id"), **{k: v for k, v in details.items() if k != "scheme_id"}}
