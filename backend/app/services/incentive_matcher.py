import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Scheme


class IncentiveMatcher:
    """Match projects to applicable government incentive schemes"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_matching_schemes(self, project_data: dict) -> list:
        """
        Find matching schemes for a project based on criteria
        """
        result = await self.db.execute(
            select(Scheme).where(Scheme.is_active == True)
        )
        all_schemes = result.scalars().all()

        matches = []

        for scheme in all_schemes:
            score = self._calculate_match_score(project_data, scheme)
            if score > 0:
                matches.append(self._scheme_payload(scheme, score, project_data))

        return sorted(matches, key=lambda x: x["match_score"], reverse=True)

    def _scheme_payload(self, scheme: Scheme, score: float, project_data: dict) -> dict:
        return {
            "id": str(scheme.id),
            "name": scheme.name,
            "department": scheme.department,
            "sector": scheme.sector,
            "location": scheme.location,
            "min_investment": scheme.min_investment,
            "max_investment": scheme.max_investment,
            "employee_requirement": scheme.employee_requirement,
            "eligible_entity": scheme.eligible_entity,
            "benefits": scheme.benefits or [],
            "application_period": scheme.application_period,
            "required_documents": scheme.required_documents or [],
            "source": scheme.source,
            "source_url": scheme.source_url,
            "match_score": score,
            "match_reason": self._generate_explanation(project_data, scheme, score),
        }

    def _calculate_match_score(self, project_data: dict, scheme: Scheme) -> float:
        """
        Calculate matching score between project and scheme (0-100)
        """
        score = 0.0

        industry = (project_data.get("industry") or project_data.get("sector") or "").lower()
        sector = (scheme.sector or "").lower()

        if sector and sector in industry or sector == "all":
            score += 30

        state = (project_data.get("state") or project_data.get("location") or "").lower()
        if scheme.location and state:
            if scheme.location.lower() == state:
                score += 25
        elif scheme.location and not state:
            score += 25

        investment = project_data.get("investment_amount")
        if isinstance(investment, (int, float)):
            meets_min = scheme.min_investment is None or investment >= scheme.min_investment
            meets_max = scheme.max_investment is None or investment <= scheme.max_investment
            if meets_min and meets_max:
                score += 20

        employees = project_data.get("employees")
        if isinstance(employees, (int, float)) and (
            (scheme.employee_requirement and employees >= scheme.employee_requirement)
            or (not scheme.employee_requirement)
        ):
            score += 15

        if project_data.get("is_women_led") or project_data.get("is_sc_st_owned"):
            score += 10

        return min(score, 100)

    def _generate_explanation(self, project_data: dict, scheme: Scheme, score: float) -> str:
        """Generate explanation for scheme match"""
        reasons = []

        if score >= 80:
            reasons.append(f"Excellent match with {scheme.name}")
        elif score >= 60:
            reasons.append(f"Good match - meets most criteria for {scheme.name}")
        else:
            reasons.append(f"Partial eligibility for {scheme.name}")

        industry = (project_data.get("industry") or project_data.get("sector") or "").lower()
        sector = (scheme.sector or "").lower()
        if sector and sector in industry:
            reasons.append(f"Your sector ({project_data.get('industry') or project_data.get('sector')}) is eligible")

        investment = project_data.get("investment_amount")
        if isinstance(investment, (int, float)) and scheme.min_investment and investment >= scheme.min_investment:
            reasons.append("Investment amount exceeds the minimum requirement")

        return " | ".join(reasons)

    async def get_scheme_details(self, scheme_id: str) -> dict:
        """Get detailed information about a scheme"""
        try:
            scheme_uuid = UUID(str(scheme_id))
        except (ValueError, AttributeError, TypeError):
            return {}

        result = await self.db.execute(
            select(Scheme).where(Scheme.id == scheme_uuid)
        )
        scheme = result.scalar_one_or_none()

        if not scheme:
            return {}

        return {
            "scheme_id": str(scheme.id),
            "name": scheme.name,
            "department": scheme.department,
            "sector": scheme.sector,
            "location": scheme.location,
            "min_investment": scheme.min_investment,
            "max_investment": scheme.max_investment,
            "eligible_entity": scheme.eligible_entity,
            "employee_requirement": scheme.employee_requirement,
            "benefits": scheme.benefits or [],
            "application_period": scheme.application_period,
            "required_documents": scheme.required_documents or [],
            "source": scheme.source,
            "source_url": scheme.source_url,
        }

    async def calculate_subsidy_amount(
        self,
        scheme_id: str,
        investment_amount: float,
        project_data: dict
    ) -> dict:
        """Calculate potential subsidy amount for a scheme"""
        details = await self.get_scheme_details(scheme_id)
        if not details:
            return {"error": "Scheme not found"}

        max_subsidy_percent = self._extract_subsidy_percent(details["benefits"]) or 25
        base_subsidy = (investment_amount * max_subsidy_percent) / 100

        bonus_percent = 0
        if project_data.get("is_women_led"):
            bonus_percent += 5
        if project_data.get("is_sc_st_owned"):
            bonus_percent += 5
        if project_data.get("is_green_compliant"):
            bonus_percent += 10

        final_subsidy = base_subsidy * (1 + bonus_percent / 100)

        return {
            "scheme_id": str(scheme_id),
            "scheme_name": details["name"],
            "investment_amount": investment_amount,
            "assumed_subsidy_percent": max_subsidy_percent,
            "base_subsidy": round(base_subsidy, 2),
            "bonus_percent": bonus_percent,
            "final_subsidy": round(final_subsidy, 2),
            "incentive_type": "capital",
            "breakdown": {
                "capital_subsidy": round(final_subsidy * 0.7, 2),
                "interest_subsidy": round(final_subsidy * 0.3, 2),
            }
        }

    @staticmethod
    def _extract_subsidy_percent(benefits: list) -> float | None:
        """Extract a subsidy percentage from benefit strings like '25% subsidy'."""
        for benefit in benefits or []:
            match = re.search(r"(\d+(?:\.\d+)?)\s*%", str(benefit))
            if match:
                return float(match.group(1))
        return None