from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_owned_approval, get_owned_project, require_auth, require_project_owner
from app.core.database import get_db_session
from app.services.compliance_tracker import ComplianceTracker
from app.services.incentive_matcher import IncentiveMatcher
from app.services.scenario_simulator import ScenarioSimulator

router = APIRouter(tags=["business-intelligence"])


class ScenarioRequest(BaseModel):
    scenario_type: str
    project_data: dict
    parameters: dict = Field(default_factory=dict)


class ProjectScenarioRequest(BaseModel):
    scenario_type: str
    parameters: dict = Field(default_factory=dict)


@router.get("/compliance/{project_id}/score")
async def get_compliance_score(
    project_id: UUID,
    project: object = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db_session),
):
    tracker = ComplianceTracker(db)
    score_data = await tracker.get_compliance_score(str(project_id))
    return score_data


@router.get("/compliance/{project_id}/alerts")
async def get_compliance_alerts(
    project_id: UUID,
    project: object = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db_session),
):
    tracker = ComplianceTracker(db)
    alerts = await tracker.get_compliance_alerts(str(project_id))
    return {"project_id": str(project_id), "alerts": alerts}


@router.get("/compliance/approval/{approval_id}")
async def get_approval_compliance(
    approval_id: UUID,
    approval: object = Depends(get_owned_approval),
    db: AsyncSession = Depends(get_db_session),
):
    tracker = ComplianceTracker(db)
    requirements = await tracker.get_compliance_requirements(str(approval_id))
    return requirements


@router.post("/schemes/match")
async def find_matching_schemes(
    project_data: dict,
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    matcher = IncentiveMatcher(db)
    matches = await matcher.find_matching_schemes(project_data)
    return {"matches": matches}


@router.get("/schemes/{scheme_id}")
async def get_scheme_details(
    scheme_id: str,
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    matcher = IncentiveMatcher(db)
    details = await matcher.get_scheme_details(scheme_id)
    if not details:
        raise HTTPException(status_code=404, detail="Scheme not found")
    return details


@router.post("/schemes/{scheme_id}/calculate-subsidy")
async def calculate_subsidy(
    scheme_id: str,
    investment_amount: float,
    project_data: dict,
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    matcher = IncentiveMatcher(db)
    subsidy = await matcher.calculate_subsidy_amount(scheme_id, investment_amount, project_data)
    if "error" in subsidy:
        raise HTTPException(status_code=404, detail=subsidy["error"])
    return subsidy


@router.get("/simulate/catalog")
async def scenario_catalog(user: dict = Depends(require_auth)):
    """Return the supported scenario types and their required planning inputs."""
    return {
        "scenarios": ScenarioSimulator.scenario_catalog(),
        "note": "Scenario modelling is advisory and does not determine statutory approvals or government outcomes.",
    }


@router.post("/simulate/projects/{project_id}")
async def run_project_scenario(
    project_id: UUID,
    req: ProjectScenarioRequest,
    project: object = Depends(get_owned_project),
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    """Run a read-only, project-aware scenario simulation."""
    try:
        return await ScenarioSimulator(db).simulate_project(
            project,
            req.scenario_type,
            req.parameters,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/simulate/scenario")
async def run_scenario_simulation(req: ScenarioRequest, user: dict = Depends(require_auth)):
    simulator = ScenarioSimulator()

    scenario_type = req.scenario_type.lower()
    if scenario_type == "location_change":
        result = simulator.simulate_location_change(req.project_data, req.parameters.get("new_location"))
    elif scenario_type == "sector_upgrade":
        result = simulator.simulate_sector_upgrade(req.project_data, req.parameters.get("new_sector"))
    elif scenario_type == "capacity_expansion":
        result = simulator.simulate_capacity_expansion(req.project_data, req.parameters.get("new_capacity"))
    elif scenario_type == "timeline_compression":
        result = simulator.simulate_timeline_compression(req.project_data, req.parameters.get("target_days"))
    else:
        raise HTTPException(status_code=400, detail=f"Unknown scenario type: {scenario_type}")

    return result


@router.get("/simulate/location/{project_id}")
async def simulate_location_change(
    project_id: UUID,
    new_state: str,
    new_district: str,
    owned: object = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db_session),
):
    from sqlalchemy import select

    from app.models import Project

    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    simulator = ScenarioSimulator()
    new_location = {"name": f"{new_district}, {new_state}", "state": new_state}

    impact = simulator.simulate_location_change(
        {"sector": project.sector, "investment": project.investment_amount, "location": {"state": project.location_state}},
        new_location,
    )
    return impact