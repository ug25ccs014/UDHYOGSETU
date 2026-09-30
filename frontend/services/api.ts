import axios, { AxiosInstance, AxiosError } from 'axios'
import { clearSession, getToken, setSession } from '@/lib/auth'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000,
    })

    this.client.interceptors.request.use((config) => {
      const token = getToken()
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    })

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401 && typeof window !== 'undefined') {
          clearSession()
          if (!window.location.pathname.startsWith('/login')) {
            window.location.href = '/login'
          }
        }
        return Promise.reject(error)
      },
    )
  }

  private extractErrorMessage(error: any): string {
    return error.response?.data?.detail || error.message || 'Request failed'
  }

  getToken(): string | null {
    return getToken()
  }

  getCurrentUser(): any | null {
    if (typeof window === 'undefined') return null
    try {
      const raw = localStorage.getItem('udyogsetu_user')
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  }

  setSession(token: string, user?: any) {
    setSession(token, user)
  }

  clearSession() {
    clearSession()
  }

  async register(email: string, name: string, phone: string, password: string, role: string) {
    const response = await this.client.post('/auth/register', { email, name, phone, password, role })
    return response.data
  }

  async login(email: string, password: string) {
    const response = await this.client.post('/auth/login', { email, password })
    return response.data
  }

  // ---- Business Profile + reusable Data Vault ---------------------------
  async getBusinessProfile() {
    const response = await this.client.get('/profile')
    return response.data
  }

  async updateBusinessProfile(profileData: Record<string, any>) {
    const response = await this.client.patch('/profile', profileData)
    return response.data
  }

  async verifyBusinessProfile() {
    const response = await this.client.post('/profile/verify')
    return response.data
  }

  async getBusinessProfileDocuments() {
    const response = await this.client.get('/profile/documents')
    return response.data
  }

  async addDocumentToBusinessVault(documentId: string) {
    const response = await this.client.post(`/profile/documents/${documentId}`)
    return response.data
  }

  async removeDocumentFromBusinessVault(documentId: string) {
    await this.client.delete(`/profile/documents/${documentId}`)
  }

  async createProject(projectData: any) {
    const response = await this.client.post('/projects', projectData)
    return response.data
  }

  async listProjects() {
    const response = await this.client.get('/projects')
    return response.data
  }

  async getProject(projectId: string) {
    const response = await this.client.get(`/projects/${projectId}`)
    return response.data
  }

  async getProjectCommandCenter(projectId: string) {
    const response = await this.client.get(`/command-center/projects/${projectId}`)
    return response.data
  }

  async analyzeProject(projectId: string) {
    const response = await this.client.post(`/projects/${projectId}/analyze`)
    return response.data
  }

  async getProjectApprovals(projectId: string) {
    const response = await this.client.get(`/projects/${projectId}/approvals`)
    return response.data
  }

  async getApprovalGraph(projectId: string) {
    const response = await this.client.get(`/projects/${projectId}/approval-graph`)
    return response.data
  }

  async submitApplication(applicationId: string) {
    const response = await this.client.post(`/applications/${applicationId}/submit`)
    return response.data
  }

  async getOfficerOverview() {
    const response = await this.client.get('/officer/full')
    return response.data
  }

  async getOfficerCommandCenter(params?: Record<string, any>) {
    const response = await this.client.get('/officer/command-center', { params })
    return response.data
  }

  async getSlaRiskPortfolio(projectId?: string) {
    const response = await this.client.get('/sla-risk/portfolio', {
      params: projectId ? { project_id: projectId } : undefined,
    })
    return response.data
  }

  async getSlaRiskProject(projectId: string) {
    const response = await this.client.get(`/sla-risk/project/${projectId}`)
    return response.data
  }

  async getSlaRiskApplication(applicationId: string) {
    const response = await this.client.get(`/sla-risk/application/${applicationId}`)
    return response.data
  }

  async getOfficerSlaRisk(params?: Record<string, any>) {
    const response = await this.client.get('/sla-risk/officer', { params })
    return response.data
  }

  async getScenarioCatalog() {
    const response = await this.client.get('/simulate/catalog')
    return response.data
  }

  async simulateProjectScenario(
    projectId: string,
    scenarioType: string,
    parameters: Record<string, any> = {},
  ) {
    const response = await this.client.post(`/simulate/projects/${projectId}`, {
      scenario_type: scenarioType,
      parameters,
    })
    return response.data
  }

  async uploadDocument(projectId: string, file: File) {
    const formData = new FormData()
    formData.append('file', file)
    const response = await this.client.post(`/documents/upload?project_id=${projectId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  }

  async queryRegulatoryCopilot(question: string, projectId?: string) {
    const response = await this.client.post('/chat/query', { question, project_id: projectId })
    return response.data
  }

  async getRecentRegulatoryChanges(params?: { limit?: number; department?: string; effective_status?: string }) {
    const response = await this.client.get('/regulatory/change/recent', { params })
    return response.data
  }

  async getProjectRegulatoryChanges(projectId: string, limit = 20) {
    const response = await this.client.get(`/regulatory/change/project/${projectId}`, { params: { limit } })
    return response.data
  }

  async getRegulatoryChange(documentId: string, projectId?: string) {
    const response = await this.client.get(`/regulatory/change/${documentId}`, {
      params: projectId ? { project_id: projectId } : undefined,
    })
    return response.data
  }

  async matchSchemes(industryData: any) {
    const response = await this.client.post('/schemes/match', industryData)
    return response.data
  }

  async getProjectIncentiveReadiness(projectId: string, limit = 20) {
    const response = await this.client.get(`/schemes/projects/${projectId}/readiness`, { params: { limit } })
    return response.data
  }

  async getSchemeIncentiveReadiness(projectId: string, schemeId: string) {
    const response = await this.client.get(`/schemes/projects/${projectId}/${schemeId}/readiness`)
    return response.data
  }

  async prepareIncentiveApplication(projectId: string, schemeId: string, payload?: { document_ids?: string[]; notes?: string }) {
    const response = await this.client.post(`/schemes/projects/${projectId}/${schemeId}/prepare`, payload || {})
    return response.data
  }

  async updateIncentiveCase(caseId: string, payload: { status?: string; document_ids?: string[]; notes?: string; external_reference?: string }) {
    const response = await this.client.patch(`/schemes/incentive-cases/${caseId}`, payload)
    return response.data
  }

  async getIncentiveCase(caseId: string) {
    const response = await this.client.get(`/schemes/incentive-cases/${caseId}`)
    return response.data
  }

  async getComplianceDashboard(projectId: string) {
    const response = await this.client.get(`/compliance/${projectId}`)
    return response.data
  }

  async completeComplianceItem(itemId: string, completedAt?: string) {
    const response = await this.client.post(`/compliance/items/${itemId}/complete`, {
      completed_at: completedAt,
    })
    return response.data
  }

  async getComplianceRenewals(projectId: string) {
    const response = await this.client.get(`/compliance/${projectId}/renewals`)
    return response.data
  }

  async prepareRenewal(projectId: string, approvalId: string) {
    const response = await this.client.post(`/compliance/${projectId}/renewals/${approvalId}/prepare`)
    return response.data
  }

  async getRenewal(renewalId: string) {
    const response = await this.client.get(`/compliance/renewals/${renewalId}`)
    return response.data
  }

  async updateRenewal(renewalId: string, payload: { status?: string; external_reference?: string; notes?: string; document_ids?: string[] }) {
    const response = await this.client.patch(`/compliance/renewals/${renewalId}`, payload)
    return response.data
  }

  // ---- Explore Government Services -------------------------------------
  async listServices(params?: Record<string, any>) {
    const response = await this.client.get('/explore/services', { params })
    return response.data
  }

  async getGatewayCatalog() {
    const response = await this.client.get('/gateway/catalog')
    return response.data
  }

  async getGatewayHealth() {
    const response = await this.client.get('/gateway/health')
    return response.data
  }

  async getDemoReadiness() {
    const response = await this.client.get('/demo/readiness')
    return response.data
  }

  async getServiceCategories() {
    const response = await this.client.get('/explore/services/categories')
    return response.data
  }

  async getService(serviceId: string) {
    const response = await this.client.get(`/explore/services/${serviceId}`)
    return response.data
  }

  async getServiceDocuments(serviceId: string, projectId?: string) {
    const response = await this.client.get(`/explore/services/${serviceId}/documents`, {
      params: projectId ? { project_id: projectId } : undefined,
    })
    return response.data
  }

  async checkApplicability(serviceId: string, projectId: string) {
    const response = await this.client.post(`/explore/services/${serviceId}/check-applicability`, {
      project_id: projectId,
    })
    return response.data
  }

  async addToChecklist(serviceId: string, projectId: string) {
    const response = await this.client.post(`/explore/services/${serviceId}/checklist`, {
      project_id: projectId,
    })
    return response.data
  }

  async getChecklistApproval(approvalId: string) {
    const response = await this.client.get(`/explore/checklist/${approvalId}`)
    return response.data
  }

  async startChecklistApplication(approvalId: string) {
    const response = await this.client.post(`/explore/checklist/${approvalId}/start`)
    return response.data
  }

  async attachChecklistDocument(approvalId: string, documentId: string) {
    const response = await this.client.post(`/explore/checklist/${approvalId}/attach-document`, {
      document_id: documentId,
    })
    return response.data
  }

  async detachChecklistDocument(approvalId: string, documentId: string) {
    const response = await this.client.post(`/explore/checklist/${approvalId}/detach-document`, {
      document_id: documentId,
    })
    return response.data
  }

  // ---- Applications (owner-scoped tracking) ----------------------------
  async listApplications() {
    const response = await this.client.get('/applications')
    return response.data
  }

  async getApplication(applicationId: string) {
    const response = await this.client.get(`/applications/${applicationId}`)
    return response.data
  }

  async getApplicationTransitions(applicationId: string) {
    const response = await this.client.get(`/applications/${applicationId}/transitions`)
    return response.data
  }

  async getSlaStatus(applicationId: string) {
    const response = await this.client.get(`/applications/${applicationId}/sla`)
    return response.data
  }

  async getApplicationReadiness(applicationId: string) {
    const response = await this.client.get(`/applications/${applicationId}/readiness`)
    return response.data
  }

  async getApplicationQueryCenter(applicationId: string) {
    const response = await this.client.get(`/applications/${applicationId}/query-center`)
    return response.data
  }

  async saveApplicationQueryResponse(
    applicationId: string,
    payload: { query_id: string; response_text: string; ready?: boolean },
  ) {
    const response = await this.client.patch(`/applications/${applicationId}/query-center`, payload)
    return response.data
  }

  async submitApplicationQueryResponse(
    applicationId: string,
    payload: { query_id: string; response_text?: string },
  ) {
    const response = await this.client.post(`/applications/${applicationId}/query-center/submit`, payload)
    return response.data
  }

  async getApplicationPreparation(applicationId: string) {
    const response = await this.client.get(`/applications/${applicationId}/preparation`)
    return response.data
  }

  async saveApplicationPreparation(
    applicationId: string,
    payload: {
      overrides?: Record<string, any>
      reset_fields?: string[]
      document_ids?: string[]
      mark_prepared?: boolean
    },
  ) {
    const response = await this.client.patch(`/applications/${applicationId}/preparation`, payload)
    return response.data
  }

  async validateDocument(documentId: string) {
    const response = await this.client.post(`/documents/${documentId}/validate`)
    return response.data
  }

  async attachApplicationDocument(applicationId: string, documentId: string) {
    const response = await this.client.post(`/applications/${applicationId}/documents/${documentId}`)
    return response.data
  }

  async detachApplicationDocument(applicationId: string, documentId: string) {
    const response = await this.client.delete(`/applications/${applicationId}/documents/${documentId}`)
    return response.data
  }

  async transitionApplication(applicationId: string, toStatus: string) {
    const response = await this.client.post(`/applications/${applicationId}/transition`, {
      to_status: toStatus,
    })
    return response.data
  }

  // ---- Grievances --------------------------------------------------------
  async listGrievances(params?: Record<string, any>) {
    const response = await this.client.get('/grievances', { params })
    return response.data
  }

  async getGrievance(grievanceId: string) {
    const response = await this.client.get(`/grievances/${grievanceId}`)
    return response.data
  }

  async listGrievanceOfficers() {
    const response = await this.client.get('/grievances/officers')
    return response.data
  }

  async getGrievanceSummary() {
    const response = await this.client.get('/grievances/summary')
    return response.data
  }

  async createGrievance(payload: {
    application_id?: string
    project_id?: string
    category: string
    subject: string
    description: string
    priority: string
  }) {
    const response = await this.client.post('/grievances', payload)
    return response.data
  }

  async transitionGrievance(grievanceId: string, payload: {
    to_status: string
    note?: string
    assigned_officer_id?: string
    resolution_note?: string
  }) {
    const response = await this.client.post(`/grievances/${grievanceId}/transition`, payload)
    return response.data
  }

  async escalateGrievance(grievanceId: string, reason: string) {
    const response = await this.client.post(`/grievances/${grievanceId}/escalate`, { reason })
    return response.data
  }

  // ---- Notifications -----------------------------------------------------
  async listNotifications(params?: {
    unread_only?: boolean
    category?: string
    severity?: string
    limit?: number
    offset?: number
  }) {
    const response = await this.client.get('/notifications', { params })
    return response.data
  }

  async getNotificationSummary() {
    const response = await this.client.get('/notifications/summary')
    return response.data
  }

  async getUnreadNotificationCount() {
    const response = await this.client.get('/notifications/unread-count')
    return response.data
  }

  async markNotificationRead(notificationId: string) {
    const response = await this.client.post(`/notifications/${notificationId}/read`)
    return response.data
  }

  async markAllNotificationsRead(category?: string) {
    const response = await this.client.post('/notifications/read-all', undefined, {
      params: category ? { category } : undefined,
    })
    return response.data
  }

  // ---- Inspections -------------------------------------------------------
  async listInspections(params?: Record<string, any>) {
    const response = await this.client.get('/inspections', { params })
    return response.data
  }

  async getApplicationInspections(applicationId: string) {
    const response = await this.client.get(`/inspections/application/${applicationId}`)
    return response.data
  }

  async getInspectionCoordinationSuggestions(projectId?: string) {
    const response = await this.client.get('/inspections/coordination-suggestions', {
      params: projectId ? { project_id: projectId } : undefined,
    })
    return response.data
  }

  async listInspectionOfficers() {
    const response = await this.client.get('/inspections/officers')
    return response.data
  }

  async scheduleInspection(payload: {
    approval_ids: string[]
    scheduled_start: string
    scheduled_end: string
    assigned_officer_id?: string
    location?: string
    notes?: string
  }) {
    const response = await this.client.post('/inspections/schedule', payload)
    return response.data
  }

  async updateInspection(inspectionId: string, payload: {
    scheduled_start?: string
    scheduled_end?: string
    assigned_officer_id?: string
    location?: string
    notes?: string
    status?: string
    checklist?: Array<{ id: string; label: string; completed: boolean }>
  }) {
    const response = await this.client.patch(`/inspections/${inspectionId}`, payload)
    return response.data
  }

  // ---- Officer review ----------------------------------------------------
  async officerListApplications(params?: Record<string, any>) {
    const response = await this.client.get('/officer/applications', { params })
    return response.data
  }

  async officerGetApplication(applicationId: string) {
    const response = await this.client.get(`/officer/applications/${applicationId}`)
    return response.data
  }

  async officerTransitionApplication(applicationId: string, toStatus: string) {
    const response = await this.client.post(`/officer/applications/${applicationId}/transition`, {
      to_status: toStatus,
    })
    return response.data
  }

  async officerSyncApplication(applicationId: string) {
    const response = await this.client.post(`/officer/applications/${applicationId}/sync`)
    return response.data
  }
}

export const apiClient = new ApiClient()
export { API_URL }