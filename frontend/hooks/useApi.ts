import { useQuery, useMutation } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import {
  cacheApprovalGraph,
  cacheProjectApprovals,
  cacheProjectCommandCenter,
  cacheApplications,
  cacheApplication,
  cacheApplicationSla,
  cacheApplicationReadiness,
  cacheProjectSummary,
  readApprovalGraph,
  readProjectApprovals,
  readProjectCommandCenter,
  readApplications,
  readCachedApplication,
  readCachedApplicationSla,
  readCachedApplicationReadiness,
  readProjectSummary,
  isOffline,
  cacheApplicationPreparation,
  readCachedApplicationPreparation,
} from '@/lib/offline'

export function useProject(projectId: string) {
  return useQuery({
    queryKey: ['project', projectId],
    queryFn: async () => {
      if (isOffline()) {
        const cached = readProjectSummary(projectId)
        if (cached) return { ...cached.data, __offlineCachedAt: cached.savedAt }
      }
      try {
        const data = await apiClient.getProject(projectId)
        cacheProjectSummary(data)
        return data
      } catch (error) {
        const cached = readProjectSummary(projectId)
        if (cached) return { ...cached.data, __offlineCachedAt: cached.savedAt }
        throw error
      }
    },
    enabled: !!projectId,
  })
}

export function useProjectCommandCenter(projectId: string) {
  return useQuery({
    queryKey: ['project-command-center', projectId],
    queryFn: async () => {
      if (isOffline()) {
        const cached = readProjectCommandCenter(projectId)
        if (cached) return { ...cached.data, __offlineCachedAt: cached.savedAt }
      }
      try {
        const data = await apiClient.getProjectCommandCenter(projectId)
        cacheProjectCommandCenter(projectId, data)
        return data
      } catch (error) {
        const cached = readProjectCommandCenter(projectId)
        if (cached) return { ...cached.data, __offlineCachedAt: cached.savedAt }
        throw error
      }
    },
    enabled: !!projectId,
  })
}

export function useBusinessProfile() {
  return useQuery({
    queryKey: ['business-profile'],
    queryFn: () => apiClient.getBusinessProfile(),
  })
}

export function useUpdateBusinessProfile() {
  return useMutation({
    mutationFn: (profileData: Record<string, any>) => apiClient.updateBusinessProfile(profileData),
  })
}

export function useVerifyBusinessProfile() {
  return useMutation({
    mutationFn: () => apiClient.verifyBusinessProfile(),
  })
}

export function useBusinessProfileDocuments() {
  return useQuery({
    queryKey: ['business-profile-documents'],
    queryFn: () => apiClient.getBusinessProfileDocuments(),
  })
}

export function useAddDocumentToBusinessVault() {
  return useMutation({
    mutationFn: (documentId: string) => apiClient.addDocumentToBusinessVault(documentId),
  })
}

export function useRemoveDocumentFromBusinessVault() {
  return useMutation({
    mutationFn: (documentId: string) => apiClient.removeDocumentFromBusinessVault(documentId),
  })
}

export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: () => apiClient.listProjects(),
  })
}

export function useProjectApprovals(projectId: string) {
  return useQuery({
    queryKey: ['project-approvals', projectId],
    queryFn: async () => {
      if (isOffline()) {
        const cached = readProjectApprovals(projectId)
        if (cached) return cached.data
      }
      try {
        const data = await apiClient.getProjectApprovals(projectId)
        cacheProjectApprovals(projectId, data)
        return data
      } catch (error) {
        const cached = readProjectApprovals(projectId)
        if (cached) return cached.data
        throw error
      }
    },
    enabled: !!projectId,
  })
}

export function useApprovalGraph(projectId: string) {
  return useQuery({
    queryKey: ['approval-graph', projectId],
    queryFn: async () => {
      if (isOffline()) {
        const cached = readApprovalGraph(projectId)
        if (cached) return { ...cached.data, __offlineCachedAt: cached.savedAt }
      }
      try {
        const data = await apiClient.getApprovalGraph(projectId)
        cacheApprovalGraph(projectId, data)
        return data
      } catch (error) {
        const cached = readApprovalGraph(projectId)
        if (cached) return { ...cached.data, __offlineCachedAt: cached.savedAt }
        throw error
      }
    },
    enabled: !!projectId,
  })
}

export function useOfficerOverview() {
  return useQuery({
    queryKey: ['officer-overview'],
    queryFn: () => apiClient.getOfficerOverview(),
  })
}

export function useOfficerCommandCenter(params?: Record<string, any>, enabled = true) {
  return useQuery({
    queryKey: ['officer-command-center', params],
    queryFn: () => apiClient.getOfficerCommandCenter(params),
    enabled,
    staleTime: 30_000,
  })
}

export function useSlaRiskPortfolio(enabled = true, projectId?: string) {
  return useQuery({
    queryKey: ['sla-risk-portfolio', projectId],
    queryFn: () => apiClient.getSlaRiskPortfolio(projectId),
    enabled,
  })
}

export function useSlaRiskProject(projectId: string, enabled = true) {
  return useQuery({
    queryKey: ['sla-risk-project', projectId],
    queryFn: () => apiClient.getSlaRiskProject(projectId),
    enabled: enabled && !!projectId,
  })
}

export function useSlaRiskApplication(applicationId: string) {
  return useQuery({
    queryKey: ['sla-risk-application', applicationId],
    queryFn: () => apiClient.getSlaRiskApplication(applicationId),
    enabled: !!applicationId,
  })
}

export function useOfficerSlaRisk(params?: Record<string, any>, enabled = true) {
  return useQuery({
    queryKey: ['officer-sla-risk', params],
    queryFn: () => apiClient.getOfficerSlaRisk(params),
    enabled,
  })
}

export function useScenarioCatalog() {
  return useQuery({
    queryKey: ['scenario-catalog'],
    queryFn: () => apiClient.getScenarioCatalog(),
    staleTime: 5 * 60_000,
  })
}

export function useSimulateProjectScenario() {
  return useMutation({
    mutationFn: ({ projectId, scenarioType, parameters }: {
      projectId: string
      scenarioType: string
      parameters?: Record<string, any>
    }) => apiClient.simulateProjectScenario(projectId, scenarioType, parameters || {}),
  })
}

export function useCreateProject() {
  return useMutation({
    mutationFn: (projectData: any) => apiClient.createProject(projectData),
  })
}

export function useAnalyzeProject() {
  return useMutation({
    mutationFn: (projectId: string) => apiClient.analyzeProject(projectId),
  })
}

export function useUploadDocument() {
  return useMutation({
    mutationFn: ({ projectId, file }: { projectId: string; file: File }) =>
      apiClient.uploadDocument(projectId, file),
  })
}

export function useRegulatoryQuery() {
  return useMutation({
    mutationFn: ({ question, projectId }: { question: string; projectId?: string }) =>
      apiClient.queryRegulatoryCopilot(question, projectId),
  })
}

export function useMatchSchemes() {
  return useMutation({
    mutationFn: (industryData: any) => apiClient.matchSchemes(industryData),
  })
}

export function useProjectIncentiveReadiness(projectId: string) {
  return useQuery({
    queryKey: ['project-incentive-readiness', projectId],
    queryFn: () => apiClient.getProjectIncentiveReadiness(projectId),
    enabled: !!projectId,
    staleTime: 60_000,
  })
}

export function useSchemeIncentiveReadiness(projectId: string, schemeId: string, enabled = true) {
  return useQuery({
    queryKey: ['scheme-incentive-readiness', projectId, schemeId],
    queryFn: () => apiClient.getSchemeIncentiveReadiness(projectId, schemeId),
    enabled: enabled && !!projectId && !!schemeId,
    staleTime: 60_000,
  })
}

export function usePrepareIncentiveApplication() {
  return useMutation({
    mutationFn: ({ projectId, schemeId, documentIds, notes }: { projectId: string; schemeId: string; documentIds?: string[]; notes?: string }) =>
      apiClient.prepareIncentiveApplication(projectId, schemeId, { document_ids: documentIds || [], notes }),
  })
}

export function useUpdateIncentiveCase() {
  return useMutation({
    mutationFn: ({ caseId, payload }: { caseId: string; payload: { status?: string; document_ids?: string[]; notes?: string; external_reference?: string } }) =>
      apiClient.updateIncentiveCase(caseId, payload),
  })
}

export function useRecentRegulatoryChanges(params?: { limit?: number; department?: string; effective_status?: string }, enabled = true) {
  return useQuery({
    queryKey: ['regulatory-changes', params],
    queryFn: () => apiClient.getRecentRegulatoryChanges(params),
    enabled,
    staleTime: 60_000,
  })
}

export function useProjectRegulatoryChanges(projectId: string, enabled = true) {
  return useQuery({
    queryKey: ['project-regulatory-changes', projectId],
    queryFn: () => apiClient.getProjectRegulatoryChanges(projectId),
    enabled: enabled && !!projectId,
    staleTime: 60_000,
  })
}

export function useRegulatoryChange(documentId: string, projectId?: string, enabled = true) {
  return useQuery({
    queryKey: ['regulatory-change', documentId, projectId],
    queryFn: () => apiClient.getRegulatoryChange(documentId, projectId),
    enabled: enabled && !!documentId,
    staleTime: 60_000,
  })
}

export function useComplianceDashboard(projectId: string) {
  return useQuery({
    queryKey: ['compliance', projectId],
    queryFn: () => apiClient.getComplianceDashboard(projectId),
    enabled: !!projectId,
  })
}

export function useCompleteComplianceItem() {
  return useMutation({
    mutationFn: ({ itemId, completedAt }: { itemId: string; completedAt?: string }) =>
      apiClient.completeComplianceItem(itemId, completedAt),
  })
}

export function usePrepareRenewal() {
  return useMutation({
    mutationFn: ({ projectId, approvalId }: { projectId: string; approvalId: string }) =>
      apiClient.prepareRenewal(projectId, approvalId),
  })
}

export function useUpdateRenewal() {
  return useMutation({
    mutationFn: ({ renewalId, payload }: { renewalId: string; payload: { status?: string; external_reference?: string; notes?: string; document_ids?: string[] } }) =>
      apiClient.updateRenewal(renewalId, payload),
  })
}

export function useGatewayCatalog(enabled = true) {
  return useQuery({
    queryKey: ['gateway-catalog'],
    queryFn: () => apiClient.getGatewayCatalog(),
    enabled,
    staleTime: 60_000,
  })
}

export function useGatewayHealth(enabled = false) {
  return useQuery({
    queryKey: ['gateway-health'],
    queryFn: () => apiClient.getGatewayHealth(),
    enabled,
    staleTime: 30_000,
  })
}

// ---- Explore Government Services ----------------------------------------
export function useServices(params?: Record<string, any>) {
  return useQuery({
    queryKey: ['explore-services', params],
    queryFn: () => apiClient.listServices(params),
  })
}

export function useServiceCategories() {
  return useQuery({
    queryKey: ['explore-categories'],
    queryFn: () => apiClient.getServiceCategories(),
  })
}

export function useService(serviceId: string) {
  return useQuery({
    queryKey: ['explore-service', serviceId],
    queryFn: () => apiClient.getService(serviceId),
    enabled: !!serviceId,
  })
}

export function useServiceDocuments(serviceId: string, projectId?: string) {
  return useQuery({
    queryKey: ['explore-service-documents', serviceId, projectId],
    queryFn: () => apiClient.getServiceDocuments(serviceId, projectId),
    enabled: !!serviceId,
  })
}

export function useCheckApplicability() {
  return useMutation({
    mutationFn: ({ serviceId, projectId }: { serviceId: string; projectId: string }) =>
      apiClient.checkApplicability(serviceId, projectId),
  })
}

export function useAddToChecklist() {
  return useMutation({
    mutationFn: ({ serviceId, projectId }: { serviceId: string; projectId: string }) =>
      apiClient.addToChecklist(serviceId, projectId),
  })
}

export function useStartChecklistApplication() {
  return useMutation({
    mutationFn: (approvalId: string) => apiClient.startChecklistApplication(approvalId),
  })
}

export function useAttachChecklistDocument() {
  return useMutation({
    mutationFn: ({ approvalId, documentId }: { approvalId: string; documentId: string }) =>
      apiClient.attachChecklistDocument(approvalId, documentId),
  })
}

export function useDetachChecklistDocument() {
  return useMutation({
    mutationFn: ({ approvalId, documentId }: { approvalId: string; documentId: string }) =>
      apiClient.detachChecklistDocument(approvalId, documentId),
  })
}

// ---- Applications --------------------------------------------------------
export function useApplications() {
  return useQuery({
    queryKey: ['applications'],
    queryFn: async () => {
      if (isOffline()) {
        const cached = readApplications()
        if (cached) return { ...cached.data, __offlineCachedAt: cached.savedAt }
      }
      try {
        const data = await apiClient.listApplications()
        cacheApplications(data)
        return data
      } catch (error) {
        const cached = readApplications()
        if (cached) return { ...cached.data, __offlineCachedAt: cached.savedAt }
        throw error
      }
    },
  })
}

export function useApplication(applicationId: string) {
  return useQuery({
    queryKey: ['application', applicationId],
    queryFn: async () => {
      if (isOffline()) {
        const cached = readCachedApplication(applicationId)
        if (cached) return { ...cached.data, __offlineCachedAt: cached.savedAt }
      }
      try {
        const data = await apiClient.getApplication(applicationId)
        cacheApplication(applicationId, data)
        return data
      } catch (error) {
        const cached = readCachedApplication(applicationId)
        if (cached) return { ...cached.data, __offlineCachedAt: cached.savedAt }
        throw error
      }
    },
    enabled: !!applicationId,
  })
}

export function useApplicationTransitions(applicationId: string) {
  return useQuery({
    queryKey: ['application-transitions', applicationId],
    queryFn: () => apiClient.getApplicationTransitions(applicationId),
    enabled: !!applicationId,
  })
}

export function useSlaStatus(applicationId: string) {
  return useQuery({
    queryKey: ['application-sla', applicationId],
    queryFn: async () => {
      if (isOffline()) {
        const cached = readCachedApplicationSla(applicationId)
        if (cached) return { ...cached.data, __offlineCachedAt: cached.savedAt }
      }
      try {
        const data = await apiClient.getSlaStatus(applicationId)
        cacheApplicationSla(applicationId, data)
        return data
      } catch (error) {
        const cached = readCachedApplicationSla(applicationId)
        if (cached) return { ...cached.data, __offlineCachedAt: cached.savedAt }
        throw error
      }
    },
    enabled: !!applicationId,
  })
}

export function useApplicationReadiness(applicationId: string) {
  return useQuery({
    queryKey: ['application-readiness', applicationId],
    queryFn: async () => {
      if (isOffline()) {
        const cached = readCachedApplicationReadiness(applicationId)
        if (cached) return { ...cached.data, __offlineCachedAt: cached.savedAt }
      }
      try {
        const data = await apiClient.getApplicationReadiness(applicationId)
        cacheApplicationReadiness(applicationId, data)
        return data
      } catch (error) {
        const cached = readCachedApplicationReadiness(applicationId)
        if (cached) return { ...cached.data, __offlineCachedAt: cached.savedAt }
        throw error
      }
    },
    enabled: !!applicationId,
  })
}

export function useApplicationQueryCenter(applicationId: string) {
  return useQuery({
    queryKey: ['application-query-center', applicationId],
    queryFn: () => apiClient.getApplicationQueryCenter(applicationId),
    enabled: !!applicationId,
  })
}

export function useSaveApplicationQueryResponse() {
  return useMutation({
    mutationFn: ({
      applicationId,
      payload,
    }: {
      applicationId: string
      payload: { query_id: string; response_text: string; ready?: boolean }
    }) => apiClient.saveApplicationQueryResponse(applicationId, payload),
  })
}

export function useSubmitApplicationQueryResponse() {
  return useMutation({
    mutationFn: ({
      applicationId,
      payload,
    }: {
      applicationId: string
      payload: { query_id: string; response_text?: string }
    }) => apiClient.submitApplicationQueryResponse(applicationId, payload),
  })
}

export function useApplicationPreparation(applicationId: string) {
  return useQuery({
    queryKey: ['application-preparation', applicationId],
    queryFn: async () => {
      if (isOffline()) {
        const cached = readCachedApplicationPreparation(applicationId)
        if (cached) return { ...cached.data, __offlineCachedAt: cached.savedAt }
      }
      try {
        const data = await apiClient.getApplicationPreparation(applicationId)
        cacheApplicationPreparation(data)
        return data
      } catch (error) {
        const cached = readCachedApplicationPreparation(applicationId)
        if (cached) return { ...cached.data, __offlineCachedAt: cached.savedAt }
        throw error
      }
    },
    enabled: !!applicationId,
  })
}

export function useSaveApplicationPreparation() {
  return useMutation({
    mutationFn: ({
      applicationId,
      payload,
    }: {
      applicationId: string
      payload: {
        overrides?: Record<string, any>
        reset_fields?: string[]
        document_ids?: string[]
        mark_prepared?: boolean
      }
    }) => apiClient.saveApplicationPreparation(applicationId, payload),
  })
}

export function useValidateDocument() {
  return useMutation({
    mutationFn: (documentId: string) => apiClient.validateDocument(documentId),
  })
}

export function useAttachApplicationDocument() {
  return useMutation({
    mutationFn: ({ applicationId, documentId }: { applicationId: string; documentId: string }) =>
      apiClient.attachApplicationDocument(applicationId, documentId),
  })
}

export function useDetachApplicationDocument() {
  return useMutation({
    mutationFn: ({ applicationId, documentId }: { applicationId: string; documentId: string }) =>
      apiClient.detachApplicationDocument(applicationId, documentId),
  })
}

export function useTransitionApplication() {
  return useMutation({
    mutationFn: ({ applicationId, toStatus }: { applicationId: string; toStatus: string }) =>
      apiClient.transitionApplication(applicationId, toStatus),
  })
}

// ---- Grievances ----------------------------------------------------------
export function useGrievances(params?: Record<string, any>) {
  return useQuery({
    queryKey: ['grievances', params],
    queryFn: () => apiClient.listGrievances(params),
  })
}

export function useGrievance(grievanceId: string) {
  return useQuery({
    queryKey: ['grievance', grievanceId],
    queryFn: () => apiClient.getGrievance(grievanceId),
    enabled: !!grievanceId,
  })
}

export function useGrievanceOfficers(enabled = true) {
  return useQuery({
    queryKey: ['grievance-officers'],
    queryFn: () => apiClient.listGrievanceOfficers(),
    enabled,
  })
}

export function useGrievanceSummary() {
  return useQuery({
    queryKey: ['grievance-summary'],
    queryFn: () => apiClient.getGrievanceSummary(),
  })
}

export function useCreateGrievance() {
  return useMutation({
    mutationFn: (payload: { application_id?: string; project_id?: string; category: string; subject: string; description: string; priority: string }) =>
      apiClient.createGrievance(payload),
  })
}

export function useTransitionGrievance() {
  return useMutation({
    mutationFn: ({ grievanceId, payload }: { grievanceId: string; payload: { to_status: string; note?: string; assigned_officer_id?: string; resolution_note?: string } }) =>
      apiClient.transitionGrievance(grievanceId, payload),
  })
}

export function useEscalateGrievance() {
  return useMutation({
    mutationFn: ({ grievanceId, reason }: { grievanceId: string; reason: string }) =>
      apiClient.escalateGrievance(grievanceId, reason),
  })
}

// ---- Notifications -------------------------------------------------------
export function useNotifications(params?: {
  unread_only?: boolean
  category?: string
  severity?: string
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: ['notifications', params],
    queryFn: () => apiClient.listNotifications(params),
    refetchInterval: 60000,
    staleTime: 30000,
  })
}

export function useNotificationSummary() {
  return useQuery({
    queryKey: ['notification-summary'],
    queryFn: () => apiClient.getNotificationSummary(),
    refetchInterval: 60000,
    staleTime: 30000,
  })
}

export function useDemoReadiness() {
  return useQuery({
    queryKey: ['demo-readiness'],
    queryFn: () => apiClient.getDemoReadiness(),
    staleTime: 30000,
  })
}

export function useUnreadNotificationCount() {
  return useQuery({
    queryKey: ['notification-unread-count'],
    queryFn: () => apiClient.getUnreadNotificationCount(),
    refetchInterval: 30000,
    staleTime: 15000,
  })
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (notificationId: string) => apiClient.markNotificationRead(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['notification-summary'] })
      queryClient.invalidateQueries({ queryKey: ['notification-unread-count'] })
    },
  })
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (category?: string) => apiClient.markAllNotificationsRead(category),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['notification-summary'] })
      queryClient.invalidateQueries({ queryKey: ['notification-unread-count'] })
    },
  })
}

// ---- Inspections ---------------------------------------------------------
export function useInspections(params?: Record<string, any>) {
  return useQuery({
    queryKey: ['inspections', params],
    queryFn: () => apiClient.listInspections(params),
  })
}

export function useApplicationInspections(applicationId: string) {
  return useQuery({
    queryKey: ['application-inspections', applicationId],
    queryFn: () => apiClient.getApplicationInspections(applicationId),
    enabled: !!applicationId,
  })
}

export function useInspectionCoordinationSuggestions(projectId?: string, enabled = true) {
  return useQuery({
    queryKey: ['inspection-coordination-suggestions', projectId],
    queryFn: () => apiClient.getInspectionCoordinationSuggestions(projectId),
    enabled,
  })
}

export function useInspectionOfficers(enabled = true) {
  return useQuery({
    queryKey: ['inspection-officers'],
    queryFn: () => apiClient.listInspectionOfficers(),
    enabled,
  })
}

export function useScheduleInspection() {
  return useMutation({
    mutationFn: (payload: {
      approval_ids: string[]
      scheduled_start: string
      scheduled_end: string
      assigned_officer_id?: string
      location?: string
      notes?: string
    }) => apiClient.scheduleInspection(payload),
  })
}

export function useUpdateInspection() {
  return useMutation({
    mutationFn: ({
      inspectionId,
      payload,
    }: {
      inspectionId: string
      payload: {
        scheduled_start?: string
        scheduled_end?: string
        assigned_officer_id?: string
        location?: string
        notes?: string
        status?: string
        checklist?: Array<{ id: string; label: string; completed: boolean }>
      }
    }) => apiClient.updateInspection(inspectionId, payload),
  })
}

// ---- Officer review -------------------------------------------------------
export function useOfficerApplications(params?: Record<string, any>) {
  return useQuery({
    queryKey: ['officer-applications', params],
    queryFn: () => apiClient.officerListApplications(params),
  })
}

export function useOfficerApplication(applicationId: string) {
  return useQuery({
    queryKey: ['officer-application', applicationId],
    queryFn: () => apiClient.officerGetApplication(applicationId),
    enabled: !!applicationId,
  })
}

export function useOfficerTransition() {
  return useMutation({
    mutationFn: ({ applicationId, toStatus }: { applicationId: string; toStatus: string }) =>
      apiClient.officerTransitionApplication(applicationId, toStatus),
  })
}

export function useOfficerSync() {
  return useMutation({
    mutationFn: (applicationId: string) => apiClient.officerSyncApplication(applicationId),
  })
}
