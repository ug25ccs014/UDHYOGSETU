var capturedClient: any

jest.mock('axios', () => {
  const makeClient = () => ({
    post: jest.fn().mockResolvedValue({ data: {} }),
    get: jest.fn().mockResolvedValue({ data: {} }),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
    defaults: { headers: {} },
  })
  const create = jest.fn(() => {
    capturedClient = makeClient()
    return capturedClient
  })
  return { create }
})

jest.mock('@/lib/auth', () => ({
  getToken: jest.fn(() => null),
  clearSession: jest.fn(),
  setSession: jest.fn(),
}))

import { apiClient } from '@/services/api'

describe('API contract: project analyze', () => {
  beforeEach(() => {
    capturedClient.post.mockReset()
    capturedClient.post.mockResolvedValue({
      data: { project_id: 'p1', applicable_approvals: [], total_count: 0 },
    })
  })

  it('POSTs to the analyze endpoint and returns the response', async () => {
    const data = await apiClient.analyzeProject('p1')
    expect(capturedClient.post).toHaveBeenCalledWith('/projects/p1/analyze')
    expect(data.total_count).toBe(0)
  })
})

describe('API contract: application submit', () => {
  beforeEach(() => {
    capturedClient.post.mockReset()
    capturedClient.post.mockResolvedValue({ data: { application_id: 'a1', status: 'SUBMITTED' } })
  })

  it('POSTs to the submit endpoint without a request body (matches backend)', async () => {
    const data = await apiClient.submitApplication('a1')
    expect(capturedClient.post).toHaveBeenCalledWith('/applications/a1/submit')
    expect(data.status).toBe('SUBMITTED')
  })
})

describe('API contract: chat query', () => {
  beforeEach(() => {
    capturedClient.post.mockReset()
    capturedClient.post.mockResolvedValue({ data: { intent: 'general', answer: 'ok' } })
  })

  it('POSTs the copilot query with a `question` field (not `query`)', async () => {
    const data = await apiClient.queryRegulatoryCopilot('What do I need?', 'p1')
    expect(capturedClient.post).toHaveBeenCalledWith('/chat/query', {
      question: 'What do I need?',
      project_id: 'p1',
    })
    expect(data.answer).toBe('ok')
  })
})


describe('Business Profile API contract', () => {
  beforeEach(() => {
    capturedClient.get.mockReset()
    capturedClient.post.mockReset()
    capturedClient.patch = jest.fn().mockResolvedValue({ data: {} })
    capturedClient.delete = jest.fn().mockResolvedValue({ data: {} })
  })

  it('gets the authenticated business profile', async () => {
    capturedClient.get.mockResolvedValue({ data: { id: 'bp1', company_name: 'ABC Textiles' } })
    const data = await apiClient.getBusinessProfile()
    expect(capturedClient.get).toHaveBeenCalledWith('/profile')
    expect(data.company_name).toBe('ABC Textiles')
  })

  it('updates the business profile with PATCH', async () => {
    capturedClient.patch.mockResolvedValue({ data: { id: 'bp1', company_name: 'Updated Co' } })
    const data = await apiClient.updateBusinessProfile({ company_name: 'Updated Co' })
    expect(capturedClient.patch).toHaveBeenCalledWith('/profile', { company_name: 'Updated Co' })
    expect(data.company_name).toBe('Updated Co')
  })

  it('runs prototype verification through the profile endpoint', async () => {
    capturedClient.post.mockResolvedValue({
      data: { verification_status: { pan: { status: 'PROTOTYPE_VERIFIED' } } },
    })
    const data = await apiClient.verifyBusinessProfile()
    expect(capturedClient.post).toHaveBeenCalledWith('/profile/verify')
    expect(data.verification_status.pan.status).toBe('PROTOTYPE_VERIFIED')
  })

  it('lists and mutates the reusable document vault', async () => {
    capturedClient.get.mockResolvedValue({ data: { documents: [], summary: {} } })
    await apiClient.getBusinessProfileDocuments()
    expect(capturedClient.get).toHaveBeenCalledWith('/profile/documents')

    capturedClient.post.mockResolvedValue({ data: { id: 'd1', in_vault: true } })
    await apiClient.addDocumentToBusinessVault('d1')
    expect(capturedClient.post).toHaveBeenCalledWith('/profile/documents/d1')

    await apiClient.removeDocumentFromBusinessVault('d1')
    expect(capturedClient.delete).toHaveBeenCalledWith('/profile/documents/d1')
  })
})


describe('Approval roadmap API contract', () => {
  beforeEach(() => {
    capturedClient.get.mockReset()
  })

  it('GETs the project approval roadmap endpoint', async () => {
    capturedClient.get.mockResolvedValue({
      data: {
        project_id: 'p1',
        summary: {
          total_count: 3,
          parallel_duration_days: 50,
          theoretical_time_saved_days: 10,
        },
      },
    })

    const data = await apiClient.getApprovalGraph('p1')
    expect(capturedClient.get).toHaveBeenCalledWith('/projects/p1/approval-graph')
    expect(data.summary.parallel_duration_days).toBe(50)
    expect(data.summary.theoretical_time_saved_days).toBe(10)
  })
})


describe('Pre-submission readiness API contract', () => {
  beforeEach(() => {
    capturedClient.get.mockReset()
    capturedClient.post.mockReset()
    capturedClient.delete.mockReset()
  })

  it('GETs readiness and exposes the readiness response', async () => {
    capturedClient.get.mockResolvedValue({
      data: { can_submit: false, readiness_state: 'BLOCKED', score: 62 },
    })
    const data = await apiClient.getApplicationReadiness('a1')
    expect(capturedClient.get).toHaveBeenCalledWith('/applications/a1/readiness')
    expect(data.readiness_state).toBe('BLOCKED')
  })

  it('POSTs document validation', async () => {
    capturedClient.post.mockResolvedValue({ data: { status: 'VERIFIED' } })
    const data = await apiClient.validateDocument('d1')
    expect(capturedClient.post).toHaveBeenCalledWith('/documents/d1/validate')
    expect(data.status).toBe('VERIFIED')
  })

  it('attaches an owned project document to an application', async () => {
    capturedClient.post.mockResolvedValue({ data: { document_id: 'd1', attached: true } })
    const data = await apiClient.attachApplicationDocument('a1', 'd1')
    expect(capturedClient.post).toHaveBeenCalledWith('/applications/a1/documents/d1')
    expect(data.attached).toBe(true)
  })
})

describe('Application preparation API contract', () => {
  beforeEach(() => {
    capturedClient.get.mockReset()
    capturedClient.patch = jest.fn().mockResolvedValue({ data: {} })
  })

  it('GETs the application preparation endpoint', async () => {
    capturedClient.get.mockResolvedValue({ data: { status: 'DRAFT', fields: [] } })
    const data = await apiClient.getApplicationPreparation('a1')
    expect(capturedClient.get).toHaveBeenCalledWith('/applications/a1/preparation')
    expect(data.status).toBe('DRAFT')
  })

  it('PATCHes application preparation overrides and returns the prepared state', async () => {
    capturedClient.patch.mockResolvedValue({ data: { status: 'PREPARED' } })
    const data = await apiClient.saveApplicationPreparation('a1', {
      overrides: { company_name: 'Project Specific Co' },
      mark_prepared: true,
    })
    expect(capturedClient.patch).toHaveBeenCalledWith('/applications/a1/preparation', {
      overrides: { company_name: 'Project Specific Co' },
      mark_prepared: true,
    })
    expect(data.status).toBe('PREPARED')
  })
})



describe('Inspection planning API contract', () => {
  beforeEach(() => {
    capturedClient.get.mockReset()
    capturedClient.post.mockReset()
    capturedClient.patch = jest.fn().mockResolvedValue({ data: {} })
  })

  it('lists inspections with optional filters', async () => {
    capturedClient.get.mockResolvedValue({ data: { inspections: [] } })
    const data = await apiClient.listInspections({ project_id: 'p1', status: 'SCHEDULED' })
    expect(capturedClient.get).toHaveBeenCalledWith('/inspections', {
      params: { project_id: 'p1', status: 'SCHEDULED' },
    })
    expect(data.inspections).toEqual([])
  })

  it('loads inspections linked to an application', async () => {
    capturedClient.get.mockResolvedValue({ data: { inspections: [{ id: 'i1' }] } })
    const data = await apiClient.getApplicationInspections('a1')
    expect(capturedClient.get).toHaveBeenCalledWith('/inspections/application/a1')
    expect(data.inspections[0].id).toBe('i1')
  })

  it('loads coordination suggestions for a project', async () => {
    capturedClient.get.mockResolvedValue({ data: { suggestions: [{ project_id: 'p1' }] } })
    const data = await apiClient.getInspectionCoordinationSuggestions('p1')
    expect(capturedClient.get).toHaveBeenCalledWith('/inspections/coordination-suggestions', {
      params: { project_id: 'p1' },
    })
    expect(data.suggestions[0].project_id).toBe('p1')
  })

  it('schedules a coordinated inspection visit', async () => {
    const payload = {
      approval_ids: ['a1', 'a2'],
      scheduled_start: '2026-10-05T10:00',
      scheduled_end: '2026-10-05T11:30',
      assigned_officer_id: 'o1',
      location: 'MIDC Ambad',
    }
    capturedClient.post.mockResolvedValue({ data: { id: 'i1', status: 'SCHEDULED' } })
    const data = await apiClient.scheduleInspection(payload)
    expect(capturedClient.post).toHaveBeenCalledWith('/inspections/schedule', payload)
    expect(data.status).toBe('SCHEDULED')
  })

  it('updates an inspection visit', async () => {
    capturedClient.patch.mockResolvedValue({ data: { id: 'i1', status: 'COMPLETED' } })
    const data = await apiClient.updateInspection('i1', { status: 'COMPLETED', notes: 'Done' })
    expect(capturedClient.patch).toHaveBeenCalledWith('/inspections/i1', {
      status: 'COMPLETED',
      notes: 'Done',
    })
    expect(data.status).toBe('COMPLETED')
  })
})

describe('SLA and smart-risk API contract', () => {
  beforeEach(() => {
    capturedClient.get.mockReset()
  })

  it('loads the authenticated SLA risk portfolio', async () => {
    capturedClient.get.mockResolvedValue({
      data: { total_applications: 2, high_risk: 1, applications: [] },
    })
    const data = await apiClient.getSlaRiskPortfolio()
    expect(capturedClient.get).toHaveBeenCalledWith('/sla-risk/portfolio', {
      params: undefined,
    })
    expect(data.high_risk).toBe(1)
  })

  it('loads the officer risk queue with filters', async () => {
    capturedClient.get.mockResolvedValue({
      data: { scope: 'OFFICER', applications: [] },
    })
    const data = await apiClient.getOfficerSlaRisk({ risk: 'HIGH', limit: 10 })
    expect(capturedClient.get).toHaveBeenCalledWith('/sla-risk/officer', {
      params: { risk: 'HIGH', limit: 10 },
    })
    expect(data.scope).toBe('OFFICER')
  })

  it('loads one enriched application risk record', async () => {
    capturedClient.get.mockResolvedValue({
      data: { risk_band: 'HIGH', risk_score: 86 },
    })
    const data = await apiClient.getSlaRiskApplication('MPCB-123')
    expect(capturedClient.get).toHaveBeenCalledWith('/sla-risk/application/MPCB-123')
    expect(data.risk_band).toBe('HIGH')
  })
})


describe('Officer Command Center API contract', () => {
  beforeEach(() => {
    capturedClient.get.mockReset()
  })

  it('loads the live officer command center with queue filters', async () => {
    capturedClient.get.mockResolvedValue({
      data: {
        scope: 'OFFICER',
        overview: { total_applications: 12, review_queue_count: 7 },
        priority_queue: [],
      },
    })

    const data = await apiClient.getOfficerCommandCenter({ department: 'MPCB', risk: 'HIGH', limit: 25 })
    expect(capturedClient.get).toHaveBeenCalledWith('/officer/command-center', {
      params: { department: 'MPCB', risk: 'HIGH', limit: 25 },
    })
    expect(data.overview.review_queue_count).toBe(7)
  })
})

describe('Regulatory Change Center API contract', () => {
  beforeEach(() => {
    capturedClient.get.mockReset()
  })

  it('loads recent regulatory changes with filters', async () => {
    capturedClient.get.mockResolvedValue({
      data: { count: 1, changes: [{ document_id: 'r1', title: 'MPCB Update', effective_status: 'ACTIVE' }] },
    })
    const data = await apiClient.getRecentRegulatoryChanges({ department: 'MPCB', effective_status: 'ACTIVE', limit: 20 })
    expect(capturedClient.get).toHaveBeenCalledWith('/regulatory/change/recent', {
      params: { department: 'MPCB', effective_status: 'ACTIVE', limit: 20 },
    })
    expect(data.changes[0].document_id).toBe('r1')
  })

  it('loads project-specific regulatory changes', async () => {
    capturedClient.get.mockResolvedValue({ data: { project_id: 'p1', changes: [] } })
    const data = await apiClient.getProjectRegulatoryChanges('p1', 10)
    expect(capturedClient.get).toHaveBeenCalledWith('/regulatory/change/project/p1', {
      params: { limit: 10 },
    })
    expect(data.project_id).toBe('p1')
  })

  it('loads a regulatory change diff with optional project impact', async () => {
    capturedClient.get.mockResolvedValue({ data: { document_id: 'r1', impact: { project_count: 2 } } })
    const data = await apiClient.getRegulatoryChange('r1', 'p1')
    expect(capturedClient.get).toHaveBeenCalledWith('/regulatory/change/r1', {
      params: { project_id: 'p1' },
    })
    expect(data.impact.project_count).toBe(2)
  })
})
