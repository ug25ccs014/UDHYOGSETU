from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRole(str, Enum):
    ENTREPRENEUR = "ENTREPRENEUR"
    OFFICER = "OFFICER"
    ADMIN = "ADMIN"


class UserRegister(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=255)
    phone: str = Field(min_length=10, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.ENTREPRENEUR

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        digits = "".join(c for c in v if c.isdigit())
        if len(digits) < 10:
            raise ValueError("Phone number must have at least 10 digits")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    phone: str
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ProjectCreate(BaseModel):
    name: str
    company_name: str
    business_type: str
    industry: str
    sector: str


class ProjectOnboarding(BaseModel):
    company_name: str = Field(min_length=2)
    business_type: str = Field(min_length=2)
    industry: str = Field(min_length=2)
    sector: str = Field(min_length=2)

    project_name: str = Field(min_length=2)
    is_new: bool = True
    project_stage: str = Field(min_length=2)
    investment_amount: float = Field(ge=0)

    location_state: str = Field(min_length=2)
    location_district: str = Field(min_length=2)
    location_city: str = Field(min_length=2)
    location_industrial_area: str | None = None
    location_midc_estate: str | None = None
    land_type: str = Field(min_length=2)

    employees: int = Field(ge=0)
    production_type: str = Field(default="", min_length=0)
    hazardous_materials: bool = False
    has_boiler: bool = False
    electricity_load: float = Field(default=0, ge=0)
    water_consumption: float = Field(default=0, ge=0)
    pollution_potential: str = "low"
    building_type: str = Field(default="", min_length=0)


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    company_name: str
    business_type: str | None = None
    industry: str
    sector: str
    project_stage: str | None = None
    investment_amount: float | None = None
    location_state: str | None = None
    location_district: str | None = None
    location_city: str | None = None
    employees: int | None = None
    hazardous_materials: bool | None = None
    has_boiler: bool | None = None
    electricity_load: float | None = None
    water_consumption: float | None = None
    pollution_potential: str | None = None
    building_type: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class BusinessProfileCompleteness(BaseModel):
    score: int
    completed_fields: int
    total_fields: int
    missing_fields: list[str] = Field(default_factory=list)
    identity_fields_present: int = 0
    identity_fields_total: int = 3


class BusinessProfileUpdate(BaseModel):
    company_name: str | None = Field(default=None, max_length=255)
    business_type: str | None = Field(default=None, max_length=100)
    industry: str | None = Field(default=None, max_length=100)
    sector: str | None = Field(default=None, max_length=100)
    pan: str | None = Field(default=None, max_length=10)
    gstin: str | None = Field(default=None, max_length=15)
    udyam_number: str | None = Field(default=None, max_length=100)
    registered_address: str | None = Field(default=None, max_length=2000)
    registered_state: str | None = Field(default=None, max_length=100)
    registered_district: str | None = Field(default=None, max_length=100)
    registered_city: str | None = Field(default=None, max_length=100)
    registered_pincode: str | None = Field(default=None, max_length=10)

    @field_validator(
        "company_name",
        "business_type",
        "industry",
        "sector",
        "pan",
        "gstin",
        "udyam_number",
        "registered_address",
        "registered_state",
        "registered_district",
        "registered_city",
        "registered_pincode",
    )
    @classmethod
    def normalize_strings(cls, value):
        if value is None:
            return None
        return value.strip()


class BusinessProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    company_name: str | None = None
    business_type: str | None = None
    industry: str | None = None
    sector: str | None = None
    pan: str | None = None
    gstin: str | None = None
    udyam_number: str | None = None
    registered_address: str | None = None
    registered_state: str | None = None
    registered_district: str | None = None
    registered_city: str | None = None
    registered_pincode: str | None = None
    verification_status: dict = Field(default_factory=dict)
    verification_details: dict = Field(default_factory=dict)
    completeness: BusinessProfileCompleteness
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApprovalResponse(BaseModel):
    id: UUID
    name: str
    department: str
    status: str
    is_mandatory: bool
    estimated_processing_days: int | None
    risk_level: str

    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    id: UUID
    file_name: str
    file_type: str
    status: str
    extracted_fields: dict
    validation_errors: list
    created_at: datetime

    class Config:
        from_attributes = True


class ComplianceItemComplete(BaseModel):
    completed_at: datetime | None = None


class RenewalUpdate(BaseModel):
    status: str | None = None
    external_reference: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=5000)
    document_ids: list[UUID] | None = None

    @field_validator("status", "external_reference", "notes")
    @classmethod
    def normalize_optional_strings(cls, value):
        if value is None:
            return None
        return value.strip()


class ComplianceItemResponse(BaseModel):
    id: UUID
    category: str
    requirement: str
    status: str
    due_date: datetime | None
    next_due: datetime | None

    class Config:
        from_attributes = True


class SchemeMatcher(BaseModel):
    industry: str
    location: str
    investment: float
    employees: int
    business_type: str


class IncentiveApplicationPrepare(BaseModel):
    document_ids: list[UUID] = Field(default_factory=list, max_length=50)
    notes: str | None = Field(default=None, max_length=5000)


class IncentiveApplicationUpdate(BaseModel):
    status: str | None = Field(default=None, max_length=40)
    document_ids: list[UUID] | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=5000)
    external_reference: str | None = Field(default=None, max_length=100)


class SchemeResponse(BaseModel):
    id: UUID
    name: str
    department: str
    sector: str | None
    min_investment: float | None
    max_investment: float | None
    benefits: list
    match_score: float | None = None
    match_reason: str | None = None

    class Config:
        from_attributes = True


class ApplicationPreparationUpdate(BaseModel):
    overrides: dict[str, object] = Field(default_factory=dict)
    reset_fields: list[str] = Field(default_factory=list)
    document_ids: list[UUID] = Field(default_factory=list)
    mark_prepared: bool = False


class ApplicationQueryResponseUpdate(BaseModel):
    query_id: UUID
    response_text: str = Field(min_length=1, max_length=20000)
    ready: bool = False


class InspectionScheduleRequest(BaseModel):
    approval_ids: list[UUID] = Field(min_length=1, max_length=10)
    scheduled_start: datetime
    scheduled_end: datetime
    assigned_officer_id: UUID | None = None
    location: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("scheduled_end")
    @classmethod
    def validate_end_after_start(cls, value: datetime, info):
        start = info.data.get("scheduled_start")
        if start and value <= start:
            raise ValueError("scheduled_end must be after scheduled_start")
        return value


class InspectionUpdateRequest(BaseModel):
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    assigned_officer_id: UUID | None = None
    location: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=5000)
    status: str | None = Field(default=None, max_length=30)
    checklist: list[dict] | None = None


class InspectionOfficerResponse(BaseModel):
    id: UUID
    name: str
    email: str


class InspectionApprovalSummary(BaseModel):
    id: UUID
    application_id: str
    name: str
    department: str
    status: str
    risk_level: str
    estimated_processing_days: int | None = None


class InspectionVisitResponse(BaseModel):
    id: UUID
    project_id: UUID
    project_name: str | None = None
    company_name: str | None = None
    assigned_officer_id: UUID | None = None
    assigned_officer_name: str | None = None
    assigned_officer_email: str | None = None
    scheduled_start: datetime
    scheduled_end: datetime
    status: str
    location: str | None = None
    notes: str | None = None
    coordination_note: str | None = None
    coordinated: bool
    approvals: list[InspectionApprovalSummary] = Field(default_factory=list)
    checklist: list[dict] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class GovernmentServiceResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str | None = None
    category: str
    authority: str
    department: str
    service_type: str
    application_mode: str
    status: str
    official_reference: str | None = None
    external_portal_url: str | None = None
    applicable_documents: list = Field(default_factory=list)
    fees: str | None = None
    eligibility_summary: str | None = None
    risk_level: str = "MEDIUM"
    sla_days: int | None = None
    renewal_period_days: int | None = None
    gateway_system: str | None = None
    is_demo: bool = False
    is_active: bool = True
    integration: dict = Field(default_factory=dict)

    class Config:
        from_attributes = True


class ExploreCheckRequest(BaseModel):
    project_id: UUID


class ExploreChecklistRequest(BaseModel):
    project_id: UUID


class ExploreDocumentAttachRequest(BaseModel):
    document_id: UUID


class GovernmentServiceCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=100)
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    category: str = Field(min_length=2, max_length=100)
    authority: str = Field(min_length=2, max_length=255)
    department: str = Field(min_length=2, max_length=100)
    service_type: str = "APPROVAL"
    application_mode: str = "GUIDED"
    official_reference: str | None = None
    external_portal_url: str | None = None
    applicable_documents: list = Field(default_factory=list)
    fees: str | None = None
    eligibility_summary: str | None = None
    risk_level: str = "MEDIUM"
    sla_days: int | None = None
    renewal_period_days: int | None = None
    approval_rule_id: UUID | None = None
    gateway_system: str | None = None
    is_demo: bool = False
    is_active: bool = True


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatQuery(BaseModel):
    question: str = Field(min_length=1)
    project_id: UUID | None = None
    language: str = "en"  # UI language: en | hi | mr (answer language only)


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]
    confidence: float
    relevant_regulations: list[str]

class GrievanceCreateRequest(BaseModel):
    application_id: str | None = Field(default=None, max_length=100)
    project_id: UUID | None = None
    category: str = Field(default="Other", min_length=1, max_length=100)
    subject: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=10, max_length=20000)
    priority: str = Field(default="MEDIUM", max_length=20)


class GrievanceTransitionRequest(BaseModel):
    to_status: str = Field(max_length=30)
    note: str | None = Field(default=None, max_length=10000)
    assigned_officer_id: UUID | None = None
    resolution_note: str | None = Field(default=None, max_length=10000)


class GrievanceEscalateRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=10000)


class GrievanceSummaryResponse(BaseModel):
    total: int
    open: int
    escalated: int
    resolved: int
    closed: int
    overdue_targets: int
    by_status: dict = Field(default_factory=dict)
    by_priority: dict = Field(default_factory=dict)
