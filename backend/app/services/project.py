from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Approval, Project
from app.schemas import ProjectOnboarding

# Fields an authenticated owner is allowed to update on their own project.
UPDATABLE_FIELDS = {
    "name", "company_name", "business_type", "industry", "sector",
    "project_stage", "investment_amount", "location_state", "location_district",
    "location_city", "location_industrial_area", "location_midc_estate",
    "land_type", "employees", "production_type", "hazardous_materials",
    "has_boiler", "electricity_load", "water_consumption",
    "pollution_potential", "building_type", "is_new", "description",
}

class ProjectService:
    """Project management service"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_project(self, project_data: ProjectOnboarding, user_id: UUID | None = None) -> Project:
        """Create a new project from onboarding data"""
        project = Project(
            user_id=user_id or UUID("00000000-0000-0000-0000-000000000000"),
            name=project_data.project_name,
            company_name=project_data.company_name,
            business_type=project_data.business_type,
            industry=project_data.industry,
            sector=project_data.sector,
            project_stage=project_data.project_stage,
            investment_amount=project_data.investment_amount,
            location_state=project_data.location_state,
            location_district=project_data.location_district,
            location_city=project_data.location_city,
            location_industrial_area=project_data.location_industrial_area,
            location_midc_estate=project_data.location_midc_estate,
            land_type=project_data.land_type,
            employees=project_data.employees,
            production_type=project_data.production_type,
            hazardous_materials=project_data.hazardous_materials,
            has_boiler=project_data.has_boiler,
            electricity_load=project_data.electricity_load,
            water_consumption=project_data.water_consumption,
            pollution_potential=project_data.pollution_potential,
            building_type=project_data.building_type,
            is_new=project_data.is_new,
        )
        
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        
        return project
    
    async def get_project(self, project_id: UUID) -> Project:
        """Get project by ID"""
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()
    
    async def list_user_projects(self, user_id: UUID) -> list[Project]:
        """List all projects owned by a user"""
        result = await self.db.execute(
            select(Project)
            .where(Project.user_id == user_id)
            .order_by(Project.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_project_approvals(self, project_id: UUID) -> list[Approval]:
        """Get all approvals for a project"""
        result = await self.db.execute(
            select(Approval).where(Approval.project_id == project_id)
        )
        return result.scalars().all()
    
    async def update_project(self, project_id: UUID, update_data: dict) -> Project:
        """Update project (only whitelisted fields are honoured)"""
        project = await self.get_project(project_id)
        if not project:
            return None
        
        nonempty = {k: v for k, v in (update_data or {}).items() if k in UPDATABLE_FIELDS and v is not None}
        for key, value in nonempty.items():
            setattr(project, key, value)
        
        project.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(project)
        
        return project
