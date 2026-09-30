import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    ENTREPRENEUR = "ENTREPRENEUR"
    OFFICER = "OFFICER"
    ADMIN = "ADMIN"

class ApprovalStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    QUERY_RAISED = "QUERY_RAISED"
    INSPECTION = "INSPECTION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELED = "CANCELED"

class DocumentStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    VERIFIED = "VERIFIED"
    WARNING = "WARNING"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    MISSING = "MISSING"

class ComplianceStatus(str, enum.Enum):
    ON_TRACK = "ON_TRACK"
    AT_RISK = "AT_RISK"
    OVERDUE = "OVERDUE"

class ServiceStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class IncentiveApplicationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PREPARING = "PREPARING"
    READY_FOR_SUBMISSION = "READY_FOR_SUBMISSION"
    SUBMITTED_EXTERNALLY = "SUBMITTED_EXTERNALLY"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class ApplicationQueryStatus(str, enum.Enum):
    OPEN = "OPEN"
    DRAFT = "DRAFT"
    READY = "READY"
    SUBMITTED = "SUBMITTED"
    RESOLVED = "RESOLVED"

class InspectionVisitStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"

class GrievanceStatus(str, enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_REVIEW = "IN_REVIEW"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"

approval_documents = Table(
    "approval_documents",
    Base.metadata,
    Column(
        "approval_id",
        UUID(as_uuid=True),
        ForeignKey("approvals.id"),
        primary_key=True,
    ),
    Column(
        "document_id",
        UUID(as_uuid=True),
        ForeignKey("documents.id"),
        primary_key=True,
    ),
)

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.ENTREPRENEUR)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    projects = relationship("Project", back_populates="owner")
    business_profile = relationship(
        "BusinessProfile",
        back_populates="owner",
        uselist=False,
        cascade="all, delete-orphan",
    )
    audit_logs = relationship("AuditLog", back_populates="user")
    assigned_inspection_visits = relationship("InspectionVisit", back_populates="assigned_officer")
    assigned_grievances = relationship("Grievance", back_populates="assigned_officer", foreign_keys="Grievance.assigned_officer_id")
    grievance_events = relationship("GrievanceEvent", back_populates="actor")
    grievances = relationship("Grievance", back_populates="user", foreign_keys="Grievance.user_id", cascade="all, delete-orphan")

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=False)
    business_type = Column(String(100))
    industry = Column(String(100))
    sector = Column(String(100))
    project_stage = Column(String(100))
    investment_amount = Column(Float)
    
    location_state = Column(String(100))
    location_district = Column(String(100))
    location_city = Column(String(100))
    location_industrial_area = Column(String(255))
    location_midc_estate = Column(String(255))
    land_type = Column(String(100))
    
    employees = Column(Integer)
    production_type = Column(String(100))
    hazardous_materials = Column(Boolean, default=False)
    has_boiler = Column(Boolean, default=False)
    electricity_load = Column(Float)
    water_consumption = Column(Float)
    pollution_potential = Column(String(50))
    building_type = Column(String(100))
    
    is_new = Column(Boolean, default=True)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    owner = relationship("User", back_populates="projects")
    approvals = relationship("Approval", back_populates="project")
    documents = relationship("Document", back_populates="project")
    compliance_items = relationship("ComplianceItem", back_populates="project")
    inspection_visits = relationship(
        "InspectionVisit",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    grievances = relationship("Grievance", back_populates="project", cascade="all, delete-orphan")
    renewal_cases = relationship("RenewalCase", back_populates="project", cascade="all, delete-orphan")
    incentive_application_cases = relationship("IncentiveApplicationCase", back_populates="project", cascade="all, delete-orphan")


inspection_visit_approvals = Table(
    "inspection_visit_approvals",
    Base.metadata,
    Column(
        "inspection_visit_id",
        UUID(as_uuid=True),
        ForeignKey("inspection_visits.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "approval_id",
        UUID(as_uuid=True),
        ForeignKey("approvals.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

business_profile_documents = Table(
    "business_profile_documents",
    Base.metadata,
    Column(
        "business_profile_id",
        UUID(as_uuid=True),
        ForeignKey("business_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "document_id",
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("added_at", DateTime, default=datetime.utcnow, nullable=False),
)


class BusinessProfile(Base):
    __tablename__ = "business_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    company_name = Column(String(255))
    business_type = Column(String(100))
    industry = Column(String(100))
    sector = Column(String(100))
    pan = Column(String(10))
    gstin = Column(String(15))
    udyam_number = Column(String(100))
    registered_address = Column(Text)
    registered_state = Column(String(100))
    registered_district = Column(String(100))
    registered_city = Column(String(100))
    registered_pincode = Column(String(10))
    verification_status = Column(JSONB, default=dict)
    verification_details = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="business_profile")
    documents = relationship(
        "Document",
        secondary="business_profile_documents",
        back_populates="business_profiles",
    )


class Approval(Base):
    __tablename__ = "approvals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    department = Column(String(100), nullable=False)
    sector = Column(String(100))
    is_mandatory = Column(Boolean, default=False)
    risk_level = Column(String(50), default="MEDIUM")
    estimated_processing_days = Column(Integer)
    renewal_period_days = Column(Integer)
    status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.NOT_STARTED)
    application_id = Column(String(100))
    submitted_at = Column(DateTime)
    approved_at = Column(DateTime)
    source = Column(String(255))
    source_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project = relationship("Project", back_populates="approvals")
    documents = relationship("Document", secondary="approval_documents")
    preparation = relationship(
        "ApplicationPreparation",
        back_populates="approval",
        uselist=False,
        cascade="all, delete-orphan",
    )
    application_queries = relationship(
        "ApplicationQuery",
        back_populates="approval",
        cascade="all, delete-orphan",
    )
    inspection_visits = relationship(
        "InspectionVisit",
        secondary="inspection_visit_approvals",
        back_populates="approvals",
    )
    renewal_case = relationship("RenewalCase", back_populates="source_approval", uselist=False, cascade="all, delete-orphan")

class ApplicationPreparation(Base):
    """Saved preparation state for an approval/application.

    Prefilled values are derived at read time from the Business Profile and
    Project. Only explicit applicant overrides are persisted, so later profile
    updates can flow into unedited application fields.
    """
    __tablename__ = "application_preparations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    approval_id = Column(
        UUID(as_uuid=True),
        ForeignKey("approvals.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    overrides = Column(JSONB, default=dict)
    prepared_snapshot = Column(JSONB, nullable=True)
    prepared_source_snapshot = Column(JSONB, nullable=True)
    status = Column(String(30), nullable=False, default="DRAFT")
    prepared_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    approval = relationship("Approval", back_populates="preparation")

class ApplicationQuery(Base):
    """Persisted lifecycle for a government query and applicant response."""
    __tablename__ = "application_queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    approval_id = Column(
        UUID(as_uuid=True),
        ForeignKey("approvals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    government_application_id = Column(String(100), nullable=True, index=True)
    system = Column(String(100), nullable=True)
    query_fingerprint = Column(String(64), nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default=ApplicationQueryStatus.OPEN.value)
    response_draft = Column(Text, nullable=True)
    submitted_response = Column(Text, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    approval = relationship("Approval", back_populates="application_queries")


class InspectionVisit(Base):
    """Scheduled on-site visit that may coordinate one or more approvals.

    A single visit can cover multiple inspection-requiring approvals for the
    same project, allowing the planning layer to coordinate a common site visit
    without changing the statutory decision process of any approval.
    """
    __tablename__ = "inspection_visits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_officer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    scheduled_start = Column(DateTime, nullable=False, index=True)
    scheduled_end = Column(DateTime, nullable=False)
    status = Column(String(30), nullable=False, default=InspectionVisitStatus.SCHEDULED.value, index=True)
    location = Column(String(1000), nullable=True)
    notes = Column(Text, nullable=True)
    checklist = Column(JSONB, default=list)
    coordination_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="inspection_visits")
    assigned_officer = relationship("User", back_populates="assigned_inspection_visits")
    approvals = relationship(
        "Approval",
        secondary="inspection_visit_approvals",
        back_populates="inspection_visits",
    )


class Grievance(Base):
    """Applicant grievance/case-management record.

    This is an internal UDYOGSETU workflow. It does not imply transmission to
    an external authority or a statutory grievance finding.
    """
    __tablename__ = "grievances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    approval_id = Column(UUID(as_uuid=True), ForeignKey("approvals.id", ondelete="SET NULL"), nullable=True, index=True)
    application_id = Column(String(100), nullable=True, index=True)
    department = Column(String(100), nullable=True, index=True)
    category = Column(String(100), nullable=False, default="Other")
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False, default="MEDIUM", index=True)
    status = Column(String(30), nullable=False, default="OPEN", index=True)
    escalation_level = Column(Integer, nullable=False, default=0)
    escalation_reason = Column(Text, nullable=True)
    assigned_officer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    response_target_at = Column(DateTime, nullable=True, index=True)
    escalated_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    resolution_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="grievances", foreign_keys=[user_id])
    project = relationship("Project", back_populates="grievances")
    approval = relationship("Approval", foreign_keys=[approval_id])
    assigned_officer = relationship("User", back_populates="assigned_grievances", foreign_keys=[assigned_officer_id])
    events = relationship("GrievanceEvent", back_populates="grievance", cascade="all, delete-orphan", order_by="GrievanceEvent.created_at")


class GrievanceEvent(Base):
    """Immutable-ish event timeline entry for a grievance."""
    __tablename__ = "grievance_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grievance_id = Column(UUID(as_uuid=True), ForeignKey("grievances.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False)
    from_status = Column(String(30), nullable=True)
    to_status = Column(String(30), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    grievance = relationship("Grievance", back_populates="events")
    actor = relationship("User", back_populates="grievance_events", foreign_keys=[actor_user_id])


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text)
    category = Column(String(50), default="general")
    severity = Column(String(20), default="info")
    is_read = Column(Boolean, default=False)
    project_id = Column(UUID(as_uuid=True), nullable=True)
    reference_id = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "title": self.title,
            "message": self.message,
            "category": self.category,
            "severity": self.severity,
            "is_read": self.is_read,
            "project_id": str(self.project_id) if self.project_id else None,
            "reference_id": self.reference_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
        }

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer)
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.UPLOADED)
    extracted_text = Column(Text)
    extracted_fields = Column(JSONB, default={})
    custom_metadata = Column(JSONB, default={})
    validation_errors = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project = relationship("Project", back_populates="documents")
    business_profiles = relationship(
        "BusinessProfile",
        secondary="business_profile_documents",
        back_populates="documents",
    )
    incentive_application_cases = relationship(
        "IncentiveApplicationCase",
        secondary="incentive_application_documents",
        back_populates="documents",
    )

class ComplianceItem(Base):
    __tablename__ = "compliance_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    category = Column(String(100), nullable=False)
    requirement = Column(String(255), nullable=False)
    frequency = Column(String(50))
    due_date = Column(DateTime)
    status = Column(SQLEnum(ComplianceStatus), default=ComplianceStatus.ON_TRACK)
    last_completed = Column(DateTime)
    next_due = Column(DateTime)
    document_required = Column(Boolean, default=False)
    source = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project = relationship("Project", back_populates="compliance_items")

class RenewalCaseStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PREPARING = "PREPARING"
    READY_FOR_SUBMISSION = "READY_FOR_SUBMISSION"
    SUBMITTED_EXTERNALLY = "SUBMITTED_EXTERNALLY"
    RENEWED = "RENEWED"
    CANCELLED = "CANCELLED"

renewal_case_documents = Table(
    "renewal_case_documents",
    Base.metadata,
    Column(
        "renewal_case_id",
        UUID(as_uuid=True),
        ForeignKey("renewal_cases.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "document_id",
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class RenewalCase(Base):
    """Operational renewal-preparation record linked to an approved approval.

    This record never mutates the original approval into a second application.
    ``SUBMITTED_EXTERNALLY`` is applicant-reported only; no government API call
    is implied by this prototype.
    """
    __tablename__ = "renewal_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    source_approval_id = Column(UUID(as_uuid=True), ForeignKey("approvals.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    status = Column(String(40), nullable=False, default=RenewalCaseStatus.DRAFT.value, index=True)
    external_reference = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    prepared_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    renewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="renewal_cases")
    source_approval = relationship("Approval", back_populates="renewal_case")
    documents = relationship("Document", secondary="renewal_case_documents")


class ApprovalRule(Base):
    __tablename__ = "approval_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    department = Column(String(100), nullable=False)
    sector = Column(String(100))
    location = Column(String(100))
    conditions = Column(JSONB, nullable=False)
    is_mandatory = Column(Boolean, default=False)
    required_documents = Column(JSON, default=[])
    dependencies = Column(JSON, default=[])
    estimated_processing_days = Column(Integer)
    renewal_period_days = Column(Integer)
    risk_level = Column(String(50), default="MEDIUM")
    source = Column(String(255))
    source_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    department = Column(String(100))
    document_type = Column(String(100))
    date = Column(DateTime)
    effective_date = Column(DateTime)
    effective_to = Column(DateTime)
    supersedes_document_id = Column(UUID(as_uuid=True), nullable=True)
    source_url = Column(String(500))
    version = Column(String(50))
    jurisdiction = Column(String(100))
    sector = Column(String(100))
    text = Column(Text, nullable=False)
    is_latest = Column(Boolean, default=True)
    superseded_by_document_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_documents.id"))
    chunk_index = Column(Integer)
    text = Column(Text, nullable=False)
    embedding = Column(JSONB)
    custom_metadata = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(UUID(as_uuid=True))
    details = Column(JSONB, default={})
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="audit_logs")

class GovernmentApplication(Base):
    """Tracks a submitted application's live state as reported by the
    government integration layer (spec §19)."""
    __tablename__ = "government_applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    approval_id = Column(UUID(as_uuid=True), ForeignKey("approvals.id"), nullable=True, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    system = Column(String(100), nullable=False)
    government_application_id = Column(String(100), nullable=False)
    last_synced_status = Column(String(50), nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    raw_response = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Scheme(Base):
    __tablename__ = "schemes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    department = Column(String(100), nullable=False)
    sector = Column(String(100))
    location = Column(String(100))
    min_investment = Column(Float)
    max_investment = Column(Float)
    eligible_entity = Column(String(100))
    employee_requirement = Column(Integer)
    benefits = Column(JSON, default=[])
    application_period = Column(String(255))
    required_documents = Column(JSON, default=[])
    source = Column(String(255))
    source_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


incentive_application_documents = Table(
    "incentive_application_documents",
    Base.metadata,
    Column(
        "incentive_application_case_id",
        UUID(as_uuid=True),
        ForeignKey("incentive_application_cases.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "document_id",
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class IncentiveApplicationCase(Base):
    """Operational preparation record for a matched incentive/scheme.

    This is intentionally separate from the Scheme catalogue and does not imply
    submission to a government system. ``SUBMITTED_EXTERNALLY`` is applicant-
    reported in the prototype.
    """
    __tablename__ = "incentive_application_cases"
    __table_args__ = (
        UniqueConstraint("project_id", "scheme_id", name="uq_incentive_case_project_scheme"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    scheme_id = Column(UUID(as_uuid=True), ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(40), nullable=False, default=IncentiveApplicationStatus.DRAFT.value, index=True)
    external_reference = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    readiness_snapshot = Column(JSONB, default=dict)
    prepared_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="incentive_application_cases")
    scheme = relationship("Scheme")
    documents = relationship("Document", secondary="incentive_application_documents")


class GovernmentService(Base):
    """Explore catalog entry for a government service.

    A service links to an ``ApprovalRule`` so the existing engine evaluates
    project applicability deterministically, and to a gateway ``system`` for
    tracked (DEMO) or guided submission flows.

    ``application_mode`` values:
      INTEGRATED - application can be created and submitted via UdyogSetu
      GUIDED     - checklist/docs prepared in UdyogSetu, submission at the authority
      REDIRECT   - "Apply" opens the official external portal
      DEMO       - mock end-to-end demonstration (is_demo should be True)
    """

    __tablename__ = "government_services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100), nullable=False, index=True)
    authority = Column(String(255), nullable=False)
    department = Column(String(100), nullable=False)
    service_type = Column(String(50), default="APPROVAL")
    application_mode = Column(String(20), default="GUIDED")
    status = Column(SQLEnum(ServiceStatus), default=ServiceStatus.ACTIVE)
    official_reference = Column(String(255))
    external_portal_url = Column(String(500))
    applicable_documents = Column(JSON, default=[])
    fees = Column(String(255))
    eligibility_summary = Column(Text)
    risk_level = Column(String(50), default="MEDIUM")
    sla_days = Column(Integer)
    renewal_period_days = Column(Integer)
    approval_rule_id = Column(UUID(as_uuid=True), ForeignKey("approval_rules.id"), nullable=True, index=True)
    gateway_system = Column(String(50), nullable=True)
    is_demo = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    approval_rule = relationship("ApprovalRule")


class AIEventLog(Base):
    """Non-sensitive observability record for AI/LLM interactions (spec §34).

    Deliberately excludes API keys, passwords and document bodies. Only metadata
    needed for cost/performance monitoring is stored.
    """

    __tablename__ = "ai_event_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    project_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    request_type = Column(String(50), nullable=False)      # generation/classification/embed/tool
    model = Column(String(100), nullable=True)             # provider/model label
    latency_ms = Column(Integer, nullable=True)
    token_count = Column(Integer, nullable=True)
    success = Column(Boolean, nullable=False, default=True)
    error_kind = Column(String(100), nullable=True)
    event_metadata = Column("metadata", JSONB, default={})  # extra, non-sensitive detail
    created_at = Column(DateTime, default=datetime.utcnow)
