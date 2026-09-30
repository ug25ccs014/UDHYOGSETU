export interface BusinessProfileVerificationState {
  status: 'NOT_PROVIDED' | 'FORMAT_VALIDATED' | 'FORMAT_INVALID' | 'PROTOTYPE_VERIFIED' | 'PROTOTYPE_REJECTED' | string
  source?: string
  verified_at?: string | null
}

export interface BusinessProfile {
  id: string
  user_id: string
  company_name?: string
  business_type?: string
  industry?: string
  sector?: string
  pan?: string
  gstin?: string
  udyam_number?: string
  registered_address?: string
  registered_state?: string
  registered_district?: string
  registered_city?: string
  registered_pincode?: string
  verification_status: Record<string, BusinessProfileVerificationState>
  verification_details: Record<string, any>
  completeness: {
    score: number
    completed_fields: number
    total_fields: number
    missing_fields: string[]
    identity_fields_present: number
    identity_fields_total: number
  }
  created_at: string
  updated_at: string
}

export interface BusinessVaultDocument extends Document {
  document_type?: string
  project_id: string
  project_name: string
  in_vault: boolean
  updated_at?: string
}

export type UserRole = 'ENTREPRENEUR' | 'OFFICER' | 'ADMIN'

export interface User {
  id: string
  email: string
  name: string
  phone: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface Project {
  id: string
  name: string
  company_name: string
  industry: string
  sector: string
  investment_amount?: number
  location_state?: string
  location_city?: string
  employees?: number
  hazardous_materials?: boolean
  has_boiler?: boolean
  electricity_load?: number
  water_consumption?: number
  pollution_potential?: string
  location_district?: string
  created_at: string
}

export interface ComplianceLifecycleItem {
  id: string
  category: string
  requirement: string
  frequency?: string | null
  status: 'ON_TRACK' | 'AT_RISK' | 'OVERDUE' | string
  due_date?: string | null
  next_due?: string | null
  last_completed?: string | null
  days_until_due?: number | null
  document_required?: boolean
  source?: string | null
  can_complete?: boolean
}

export interface RenewalCase {
  id?: string | null
  case_id?: string | null
  approval_id: string
  approval_name: string
  department: string
  renewal_date: string
  days_until_renewal: number
  advance_notice_days: number
  lifecycle_status: string
  case_status?: string | null
  prepared_at?: string | null
  submitted_at?: string | null
  renewed_at?: string | null
  external_reference?: string | null
  can_prepare?: boolean
}

export interface Approval {
  id: string
  name: string
  department: string
  status: string
  is_mandatory: boolean
  estimated_processing_days?: number
  risk_level: string
}


export interface ApprovalRoadmapNode {
  id: string
  label: string
  department: string
  days: number
  status: string
  mandatory: boolean
  risk_level?: string
  dependencies: string[]
  dependency_ids: string[]
  level: number
  earliest_start_day: number
  earliest_finish_day: number
  execution_state: 'READY' | 'BLOCKED' | 'IN_PROGRESS' | 'COMPLETED' | string
}

export interface ApprovalRoadmapEdge {
  id: string
  source: string
  target: string
  dependency: string
  on_critical_path: boolean
}

export interface ApprovalParallelGroup {
  stage: number
  approval_ids: string[]
  approval_count: number
  can_run_in_parallel: boolean
  stage_max_duration_days: number
  approvals: {
    id: string
    name: string
    department: string
    days: number
    status: string
    critical: boolean
  }[]
}

export interface ApprovalRoadmapScheduleItem {
  id: string
  name: string
  start_day: number
  finish_day: number
  duration_days: number
  level: number
  critical: boolean
}

export interface ApprovalRoadmapResponse {
  project_id: string
  nodes: ApprovalRoadmapNode[]
  edges: ApprovalRoadmapEdge[]
  parallel_groups: ApprovalParallelGroup[]
  schedule: ApprovalRoadmapScheduleItem[]
  critical_path: {
    duration_days: number
    approval_ids: string[]
    names: string[]
    approvals: {
      id: string
      name: string
      days: number
      status: string
    }[]
  }
  summary: {
    total_count: number
    mandatory_count: number
    sequential_duration_days: number
    parallel_duration_days: number
    theoretical_time_saved_days: number
    parallel_approval_count: number
    parallel_group_count: number
    critical_path_count: number
    warning: string
  }
  warnings: string[]
}

export interface Document {
  id: string
  file_name: string
  file_type: string
  status: string
  extracted_fields: Record<string, any>
  validation_errors: string[]
  created_at: string
}

export type RegulatoryEffectiveStatus = 'ACTIVE' | 'UPCOMING' | 'EXPIRED' | 'UNKNOWN' | string

export interface RegulatoryChangeItem {
  document_id: string
  title: string
  department?: string | null
  document_type?: string | null
  version: string
  previous_version?: string | null
  effective_date?: string | null
  effective_to?: string | null
  effective_status: RegulatoryEffectiveStatus
  is_latest: boolean
  text_changed: boolean
  text_change_summary: string
  similarity: number
  change_items: {
    type: 'ADDED' | 'REMOVED' | 'MODIFIED' | string
    section: string
    old_text?: string
    new_text?: string
  }[]
  changed_field_count: number
  impact: {
    potentially_affected: boolean
    approval_count: number
    project_count: number
    department?: string | null
    reason: string
  }
  source_url?: string | null
  created_at?: string | null
}

export interface RegulatoryChangeImpact {
  potentially_affected: boolean
  approval_count: number
  project_count: number
  departments: string[]
  reason: string
  current_project?: {
    project_id: string
    project_name?: string | null
    potentially_affected: boolean
    matched_approvals: {
      approval_id: string
      approval_name: string
      department: string
      status: string
    }[]
  } | null
}

export interface RegulatoryChangeDetail extends RegulatoryChangeItem {
  supersedes_document_id?: string | null
  supersedes_version?: string | null
  impact: RegulatoryChangeImpact
  changed_fields: { field: string; from: any; to: any }[]
  source: { url?: string | null; label: string }
  note: string
}

export interface Scheme {
  id: string
  name: string
  department: string
  sector?: string
  location?: string
  min_investment?: number | null
  max_investment?: number | null
  eligible_entity?: string | null
  employee_requirement?: number | null
  benefits: string[]
  application_period?: string | null
  required_documents?: string[]
  source?: string | null
  source_url?: string | null
  match_score?: number
  match_reason?: string
}

export interface IncentiveReadinessDocument {
  requirement: string
  status: string
  document_id?: string | null
  file_name?: string | null
  project_id?: string | null
  project_name?: string | null
  in_vault?: boolean
  match_score?: number
  document_status?: string
  validation_errors?: string[]
  candidates?: Array<{
    document_id: string
    file_name: string
    project_id: string
    project_name: string
    status: string
    in_vault: boolean
    match_score: number
  }>
}

export interface IncentiveReadiness {
  scheme_id: string
  name: string
  department: string
  sector?: string | null
  match_score: number
  match_reason?: string
  benefits: string[]
  application_period?: string | null
  source?: string | null
  source_url?: string | null
  eligibility: {
    criteria: Array<{ key: string; label: string; status: string; detail: string }>
    manual_confirmation_required: boolean
  }
  profile: { score: number; complete: boolean }
  required_documents: IncentiveReadinessDocument[]
  document_summary: { required: number; ready: number; missing: number; invalid: number }
  readiness_score: number
  readiness_state: string
  blockers: Array<{ code: string; message: string; document?: IncentiveReadinessDocument }>
  warnings: Array<{ code: string; message: string }>
  case: { case_id?: string | null; status?: string | null; external_reference?: string | null; prepared_at?: string | null }
  note: string
}

export interface NotificationItem {
  id: string
  title: string
  message?: string | null
  category: string
  severity: string
  is_read: boolean
  project_id?: string | null
  reference_id?: string | null
  created_at?: string | null
  read_at?: string | null
  action_path?: string | null
}

export interface NotificationSummary {
  total: number
  unread: number
  recent_24h: number
  by_category: Record<string, number>
  by_severity: Record<string, number>
}

export interface ComplianceItem {
  id: string
  category: string
  requirement: string
  status: string
  due_date?: string
  next_due?: string
}

export interface InspectionApprovalSummary {
  id: string
  application_id: string
  name: string
  department: string
  status: string
  risk_level: string
  estimated_processing_days?: number | null
}

export interface InspectionVisit {
  id: string
  project_id: string
  project_name?: string | null
  company_name?: string | null
  assigned_officer_id?: string | null
  assigned_officer_name?: string | null
  assigned_officer_email?: string | null
  scheduled_start: string
  scheduled_end: string
  status: string
  location?: string | null
  notes?: string | null
  coordination_note?: string | null
  coordinated: boolean
  approvals: InspectionApprovalSummary[]
  checklist: { id: string; label: string; completed: boolean }[]
  created_at: string
  updated_at: string
}

export interface InspectionCoordinationSuggestion {
  project_id: string
  project_name: string
  company_name: string
  location: string
  approval_ids: string[]
  applications: InspectionApprovalSummary[]
  approval_count: number
  separate_site_visits: number
  coordinated_site_visits: number
  site_visits_avoided: number
  reason: string
  note: string
}

export interface GovernmentIntegrationMetadata {
  classification: string
  label: string
  status: string
  source_label: string
  provider: string
  is_simulated: boolean
  gateway_system?: string | null
  external_portal_url?: string | null
  submission_handling?: string
  note?: string
}

export interface GovernmentIntegrationSystem extends GovernmentIntegrationMetadata {
  system: string
  display_name: string
  supports_services: boolean
  supports_status: boolean
  supports_submission: boolean
  official_portal_url?: string | null
}

export interface GovernmentService {
  id: string
  slug: string
  name: string
  description?: string
  category: string
  authority?: string
  department: string
  service_type: string
  application_mode: 'INTEGRATED' | 'GUIDED' | 'REDIRECT' | 'DEMO'
  official_reference?: string
  external_portal_url?: string
  applicable_documents?: { document_type: string; description?: string; required?: boolean }[]
  fees?: string
  eligibility_summary?: string
  risk_level: string
  sla_days?: number
  renewal_period_days?: number
  approval_rule_id?: string
  gateway_system?: string
  is_demo: boolean
  is_active: boolean
  integration?: GovernmentIntegrationMetadata
}

export interface GatewayCatalogResponse {
  provider: string
  systems: GovernmentIntegrationSystem[]
  summary: {
    total_systems: number
    configured_systems: number
    simulated_systems: number
    authorized_systems: number
    future_authorized_systems: number
    external_portal_systems: number
  }
  disclaimer: string
}

export interface ApplicabilityResult {
  service_id: string
  service_slug: string
  status: 'APPLICABLE' | 'NOT_APPLICABLE' | 'NOT_DETERMINED'
  reason: string
  matched_conditions: string[]
  failed_conditions: string[]
  required_documents: string[]
  rule_id?: string
}

export interface ServiceDocumentEntry {
  document_type: string
  description: string
  required: boolean
}

export interface ServiceDocumentsResponse {
  service_id: string
  service_slug: string
  required_documents: ServiceDocumentEntry[]
  project_id?: string
  project_documents: {
    id: string
    file_name: string
    status: string
    document_type?: string
    matches_requirement: number[]
  }[]
}

export interface ChecklistApplication {
  approval_id: string
  application_id: string
  name: string
  department: string
  status: string
  service_slug?: string
  required_documents: ServiceDocumentEntry[]
  attached_documents: {
    id: string
    file_name: string
    status: string
    document_type?: string
  }[]
  available_transitions: { to: string; label: string; side_effect: string }[]
}

export interface ApplicationItem {
  application_id: string
  approval_id?: string
  approval_name: string
  department: string
  project_name?: string
  status: string
  submitted_at?: string
  approved_at?: string
  estimated_processing_days?: number
  risk_level?: string
}

export interface ApplicationDetail extends ApplicationItem {
  documents?: { id: string; file_name: string; status: string; document_type?: string }[]
  government?: {
    system?: string
    government_application_id?: string
    last_synced_status?: string
  }
  owner_email?: string
  owner_name?: string
  company_name?: string
  source?: string
  available_transitions?: { to: string; label: string; side_effect: string }[]
}

export interface SubmissionReadinessIssue {
  code: string
  severity: 'BLOCKER' | 'WARNING' | string
  category: string
  message: string
  details?: Record<string, any>
}

export interface SubmissionReadinessCheck {
  key: string
  label: string
  status: 'PASS' | 'WARNING' | 'BLOCKED' | string
  message: string
  details?: Record<string, any>
}

export interface SubmissionReadinessDocument {
  requirement: string
  description?: string
  required: boolean
  status: 'READY' | 'MISSING' | 'INVALID' | 'VALIDATION_PENDING' | string
  document_id?: string | null
  file_name?: string | null
  document_status?: string
  available_in_vault?: boolean
  vault_document_id?: string | null
  validation_errors?: string[]
  action?: string
  candidate_documents?: {
    document_id: string
    file_name: string
    status: string
    document_type?: string | null
    match_score: number
  }[]
}

export interface SubmissionReadiness {
  application_id: string
  approval_id: string
  project_id: string
  approval_name: string
  department: string
  application_status: string
  submission_eligible: boolean
  can_submit: boolean
  readiness_state: 'READY' | 'ACTION_REQUIRED' | 'BLOCKED' | 'NOT_APPLICABLE' | string
  score: number
  summary: {
    profile_score: number
    required_documents: number
    documents_ready: number
    documents_missing: number
    documents_blocked: number
    warnings: number
    blockers: number
    cross_document_red: number
    cross_document_yellow: number
  }
  checks: SubmissionReadinessCheck[]
  document_checklist: SubmissionReadinessDocument[]
  issues: SubmissionReadinessIssue[]
  blocking_issues: SubmissionReadinessIssue[]
  warnings: SubmissionReadinessIssue[]
  next_actions: {
    priority: string
    action: string
    details: string[]
    route: string
  }[]
  sources: {
    approval_rule?: string | null
    service?: string | null
    government_api: string
  }
}

export interface ApplicationPreparationField {
  key: string
  label: string
  section: string
  source: string
  source_path: string
  required: boolean
  editable: boolean
  kind: 'text' | 'textarea' | 'number' | 'boolean' | string
  value: any
  source_value?: any
  status: 'FILLED' | 'MISSING' | 'OPTIONAL_EMPTY' | string
  effective_source: string
  source_label: string
  has_override: boolean
  source_changed?: boolean
}

export interface ApplicationQueryEvidence {
  label: string
  satisfied: boolean
  matched_documents: {
    document_id: string
    file_name: string
    document_type?: string | null
    status: string
    validation_errors?: string[]
    attached?: boolean
  }[]
}

export interface ApplicationQueryCenter {
  query_present: boolean
  project_id: string
  query_id?: string | null
  status?: string | null
  query?: string | null
  explanation?: string | null
  suggestion?: string | null
  suggested_response?: string | null
  response_draft?: string | null
  submitted_response?: string | null
  submitted_at?: string | null
  required_evidence: ApplicationQueryEvidence[]
  relevant_documents: {
    document_id: string
    file_name: string
    document_type?: string | null
    status: string
    match_score?: number
    attached?: boolean
  }[]
  available_documents: {
    document_id: string
    file_name: string
    document_type?: string | null
    status: string
    validation_errors?: string[]
    attached?: boolean
  }[]
  attached_documents: {
    document_id: string
    file_name: string
    document_type?: string | null
    status: string
  }[]
  regulatory_context: { title?: string; url?: string; score?: number }[]
  government: { system?: string | null; government_application_id?: string | null; source: string }
  can_save: boolean
  can_submit: boolean
  disclaimer?: string
}

export interface ApplicationPreparation {
  __offlineCachedAt?: string
  application_id: string
  approval_id: string
  approval_name: string
  department: string
  project_id: string
  project_name: string
  application_status: string
  status: 'DRAFT' | 'PREPARED' | 'STALE' | string
  prepared_at?: string | null
  stale_fields: string[]
  summary: {
    filled_required_fields: number
    required_fields: number
    missing_required_fields: string[]
    filled_fields: number
    total_fields: number
    preparation_score: number
    readiness_score: number
    readiness_state: string
  }
  fields: ApplicationPreparationField[]
  attached_documents: {
    id: string
    file_name: string
    status: string
    document_type?: string | null
  }[]
  recommended_documents: {
    document_id: string
    file_name: string
    status: string
    document_type?: string | null
    match_score: number
    requirements: string[]
  }[]
  sources: {
    business_profile: string
    project: string
    government_api: string
  }
  disclaimer: string
}

export interface SlaStatus {
  application_id?: string
  approval_name?: string
  status: 'ON_TRACK' | 'AT_RISK' | 'BREACHED' | 'COMPLETED' | 'NOT_STARTED'
  sla_days: number
  days_elapsed: number
  days_remaining: number
  reason: string
  breach_probability: number
  deadline?: string
}


export interface SlaRiskApplication {
  approval_id: string
  application_id: string
  approval_name: string
  department: string
  project_id: string
  project_name?: string | null
  company_name?: string | null
  project_location?: string | null
  status: string
  risk_band: 'HIGH' | 'MEDIUM' | 'LOW' | string
  risk_score: number
  breach_probability: number
  sla: {
    status: 'ON_TRACK' | 'AT_RISK' | 'BREACHED' | 'COMPLETED' | 'NOT_STARTED' | string
    sla_days: number
    days_elapsed: number
    days_remaining: number
    deadline?: string | null
    reason: string
  }
  signals: {
    query_open_count: number
    latest_query_id?: string | null
    inspection_scheduled: boolean
    inspection_status?: string | null
    next_inspection_start?: string | null
    document_issue_count: number
    government_system?: string | null
    government_source: string
  }
  key_risk_factors: string[]
  recommended_actions: string[]
  confidence: number
  predictive_assistance: boolean
  disclaimer: string
}

export interface OfficerDepartmentMetric {
  department: string
  total: number
  approved: number
  pending: number
  sla_breaches: number
  avg_days: number
  backlog: number
}

export interface OfficerBottleneck {
  name: string
  count: number
  share_percent: number
  description: string
  overlap_possible?: boolean
}

export interface OfficerCommandCenterResponse {
  scope: 'OFFICER' | string
  overview: {
    total_applications: number
    pending_review: number
    review_queue_count: number
    awaiting_applicant: number
    sla_breaches: number
    sla_on_track: number
    sla_at_risk: number
    sla_breached: number
    avg_processing_days: number
    approved: number
    rejected: number
    high_risk: number
    medium_risk: number
    action_required: number
    open_queries: number
    scheduled_inspections: number
    open_grievances: number
  }
  throughput: {
    submissions_today: number
    submissions_7d: number
    submissions_30d: number
  }
  departments: OfficerDepartmentMetric[]
  distribution: { status: string; count: number }[]
  bottlenecks: OfficerBottleneck[]
  priority_queue: SlaRiskApplication[]
  filters: { department?: string | null; risk_band?: string | null; limit?: number }
  disclaimer: string
}


export interface SlaRiskPortfolio {
  scope: 'PORTFOLIO' | 'PROJECT' | 'OFFICER' | string
  total_applications: number
  high_risk: number
  medium_risk: number
  low_risk: number
  sla_on_track: number
  sla_at_risk: number
  sla_breached: number
  action_required: number
  applications: SlaRiskApplication[]
  filters?: {
    department?: string | null
    risk_band?: string | null
    limit?: number
  }
}


export interface GrievanceEvent {
  id: string
  event_type: string
  from_status?: string | null
  to_status?: string | null
  note?: string | null
  actor_name?: string | null
  created_at?: string | null
}

export interface Grievance {
  id: string
  project_id: string
  project_name: string
  company_name: string
  approval_id?: string | null
  application_id?: string | null
  department?: string | null
  category: string
  subject: string
  description: string
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | string
  status: 'OPEN' | 'ACKNOWLEDGED' | 'IN_REVIEW' | 'ESCALATED' | 'RESOLVED' | 'CLOSED' | 'REJECTED' | string
  escalation_level: number
  escalation_reason?: string | null
  assigned_officer_id?: string | null
  assigned_officer_name?: string | null
  response_target_at?: string | null
  days_to_response_target?: number | null
  escalated_at?: string | null
  resolved_at?: string | null
  closed_at?: string | null
  resolution_note?: string | null
  created_at: string
  updated_at: string
  events: GrievanceEvent[]
  sla_context?: any
  disclaimer: string
}

export interface CommandCenterAction {
  id: string
  priority: 'HIGH' | 'MEDIUM' | 'INFO' | string
  title: string
  description: string
  target: string
  reference_id?: string | null
}

export interface CommandCenterApproval {
  id: string
  application_id: string
  name: string
  department: string
  status: string
  mandatory: boolean
  risk_level?: string | null
  estimated_processing_days?: number | null
  submitted_at?: string | null
  approved_at?: string | null
  sla: {
    status?: string | null
    days_elapsed?: number | null
    days_remaining?: number | null
    deadline?: string | null
  }
  risk: {
    band?: string | null
    score?: number | null
    factors: string[]
  }
  readiness: {
    state?: string | null
    score?: number | null
    blockers: number
    warnings: number
    next_actions: string[]
  }
  preparation: {
    status?: string | null
    prepared_at?: string | null
  }
  query: {
    open_count: number
  }
  inspection: {
    scheduled: boolean
    visit_id?: string
    scheduled_start?: string | null
    scheduled_end?: string | null
    location?: string | null
    status?: string | null
    assigned_officer_id?: string | null
  }
  renewal?: {
    type?: string
    approval_id?: string
    approval_name?: string
    days_until_renewal?: number
    severity?: string
  } | null
  action: {
    priority: string
    label?: string | null
  }
}

export interface CommandCenterResponse {
  project: {
    id: string
    name: string
    company_name: string
    industry?: string | null
    sector?: string | null
    project_stage?: string | null
    investment_amount?: number | null
    location?: string | null
    location_state?: string | null
    location_district?: string | null
    location_city?: string | null
  }
  overview: {
    project_readiness_score: number
    approval_count: number
    approved: number
    in_progress: number
    awaiting_applicant: number
    queries: number
    inspections: number
    high_risk: number
    sla_at_risk: number
    sla_breached: number
    documents_total: number
    documents_attention: number
    compliance_score: number
    renewals_due: number
    incentive_matches: number
    open_grievances: number
    action_count: number
  }
  profile: {
    exists: boolean
    completeness_score: number
    missing_fields: string[]
    identity_fields_present: number
    verification: Record<string, any>
  }
  approvals: CommandCenterApproval[]
  roadmap: {
    total_count: number
    sequential_duration_days: number
    parallel_duration_days: number
    time_saved_days: number
    parallel_group_count: number
    critical_path_days: number
    critical_path_names: string[]
    warnings: string[]
  }
  documents: {
    total: number
    ready: number
    needs_attention: number
    by_status: Record<string, number>
  }
  compliance: {
    score: number
    on_track: number
    at_risk: number
    overdue: number
    renewals: any[]
  }
  incentives: {
    count: number
    top_matches: {
      id: string
      name: string
      department?: string
      match_score?: number
      match_reason?: string
      benefits: string[]
      source_url?: string | null
    }[]
    disclaimer: string
  }
  inspections: {
    upcoming: any[]
    count: number
  }
  grievances: {
    open: number
    escalated: number
    overdue_targets: number
    items: any[]
  }
  sla_risk: {
    high_risk: number
    medium_risk: number
    low_risk: number
    sla_on_track: number
    sla_at_risk: number
    sla_breached: number
    applications: any[]
  }
  action_center: CommandCenterAction[]
  metadata: {
    generated_at: string
    government_api_status: string
    disclaimer: string
  }
}


export interface ScenarioCatalogItem {
  type: string
  label: string
  description: string
  parameters: string[]
}

export interface ScenarioRuleChange {
  name: string
  department: string
  mandatory: boolean
  risk_level: string
  estimated_processing_days: number
  required_documents: string[]
  source?: string | null
  source_url?: string | null
  change: 'ADDED' | 'REMOVED' | string
}

export interface ScenarioSimulationResponse {
  scenario: {
    type: string
    label: string
    parameters: Record<string, any>
    description: string
    meta: Record<string, any>
  }
  baseline: {
    project: Record<string, any>
    approval_count: number
    mandatory_approval_count: number
    required_document_count: number
    timeline: {
      parallel_duration_days: number
      sequential_duration_days: number
      theoretical_time_saved_days: number
      critical_path_names: string[]
    }
    high_risk_approval_count: number
    incentives: { id: string; name: string; match_score: number; match_reason?: string }[]
  }
  projected: {
    project: Record<string, any>
    approval_count: number
    mandatory_approval_count: number
    required_document_count: number
    timeline: {
      parallel_duration_days: number
      sequential_duration_days: number
      theoretical_time_saved_days: number
      critical_path_names: string[]
    }
    high_risk_approval_count: number
    incentives: { id: string; name: string; match_score: number; match_reason?: string }[]
  }
  changes: {
    approvals_added: ScenarioRuleChange[]
    approvals_removed: ScenarioRuleChange[]
    approvals_unchanged_count: number
    required_documents_added: string[]
    required_documents_removed: string[]
    timeline_delta_days: number
    sequential_timeline_delta_days: number
    parallel_savings_delta_days: number
    high_risk_approval_delta: number
    risk_change: string
    risk_indicators: string[]
    new_incentives: { id: string; name: string; match_score: number; match_reason?: string }[]
    removed_incentives: { id: string; name: string; match_score: number; match_reason?: string }[]
    incentive_score_changes: { id: string; name: string; before: number; after: number; delta: number }[]
  }
  roadmap: {
    baseline: { schedule: any[]; parallel_groups: any[]; critical_path_names: string[] }
    projected: { schedule: any[]; parallel_groups: any[]; critical_path_names: string[] }
  }
  planning_signal: Record<string, any>
  recommendations: string[]
  warnings: string[]
}
