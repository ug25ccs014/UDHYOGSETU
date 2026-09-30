import {
  cacheApprovalGraph,
  cacheApplication,
  cacheApplicationPreparation,
  cacheApplicationReadiness,
  cacheApplicationSla,
  readCachedApplicationPreparation,
  cacheProjectApprovals,
  cacheProjectSummary,
  clearAllOfflineDrafts,
  countPendingOfflineDrafts,
  deleteOfflineApplicationDraft,
  getOfflineApplicationDraft,
  isOffline,
  readApprovalGraph,
  readCachedApplication,
  readCachedApplicationReadiness,
  readCachedApplicationSla,
  readProjectApprovals,
  readProjectSummary,
  saveOfflineApplicationDraft,
} from '@/lib/offline'

const user = (id: string) => ({ id, email: `${id}@example.test` })

beforeEach(() => {
  localStorage.clear()
  Object.defineProperty(navigator, 'onLine', { configurable: true, value: true })
  localStorage.setItem('udyogsetu_user', JSON.stringify(user('u1')))
})

afterEach(() => {
  localStorage.clear()
})

describe('offline cache and draft store', () => {
  it('scopes cached projects and approvals to the signed-in user', () => {
    cacheProjectSummary({ id: 'p1', name: 'Project 1' } as any)
    cacheProjectApprovals('p1', [{ id: 'a1', name: 'Factory' }])

    expect(readProjectSummary('p1')?.data.name).toBe('Project 1')
    expect(readProjectApprovals('p1')?.data[0].id).toBe('a1')

    localStorage.setItem('udyogsetu_user', JSON.stringify(user('u2')))
    expect(readProjectSummary('p1')).toBeNull()
    expect(readProjectApprovals('p1')).toBeNull()
  })

  it('filters sensitive fields from offline application drafts and caches', () => {
    saveOfflineApplicationDraft({
      applicationId: 'MPCB-privacy',
      projectId: 'p1',
      values: { investment_amount: 100000, pan: 'ABCDE1234F', gstin: '27ABCDE1234F1Z5' },
      dirtyKeys: ['investment_amount', 'pan', 'gstin'],
      resetFields: [],
      serverValues: { investment_amount: 50000, pan: 'OLDPAN', registered_address: 'Sensitive address' },
      updatedAt: new Date().toISOString(),
      status: 'PENDING_SYNC',
    })
    const draft = getOfflineApplicationDraft('MPCB-privacy')
    expect(draft?.values).toEqual({ investment_amount: 100000 })
    expect(draft?.dirtyKeys).toEqual(['investment_amount'])
    expect(draft?.serverValues).toEqual({ investment_amount: 50000 })
    expect(draft?.blockedSensitiveKeys).toEqual(['pan', 'gstin'])

    cacheApplicationPreparation({
      application_id: 'MPCB-privacy',
      approval_id: 'a1',
      approval_name: 'MPCB Consent',
      department: 'MPCB',
      project_id: 'p1',
      project_name: 'ABC Textiles',
      application_status: 'DRAFT',
      status: 'DRAFT',
      stale_fields: [],
      summary: {
        required_fields: 1,
        filled_required_fields: 1,
        missing_required_fields: [],
        filled_fields: 2,
        total_fields: 2,
        preparation_score: 100,
        readiness_score: 100,
        readiness_state: 'READY',
      },
      fields: [
        { key: 'investment_amount', label: 'Investment', value: 100000, source_value: 100000, kind: 'number', required: true, section: 'Project', source: 'project', source_path: 'project.investment_amount', editable: true, status: 'FILLED', effective_source: 'project', source_label: 'Project', has_override: false },
        { key: 'pan', label: 'PAN', value: 'ABCDE1234F', source_value: 'ABCDE1234F', kind: 'text', required: true, section: 'Identity', source: 'business_profile', source_path: 'business_profile.pan', editable: true, status: 'FILLED', effective_source: 'business_profile', source_label: 'Business profile', has_override: false },
      ],
      attached_documents: [],
      recommended_documents: [],
      sources: { business_profile: 'Business profile', project: 'Project', government_api: 'Not connected' },
      disclaimer: 'Prototype',
    })
    const cached = readCachedApplicationPreparation('MPCB-privacy')
    expect(cached?.data.fields.find((field) => field.key === 'pan')?.value).toBeNull()
    expect(cached?.data.fields.find((field) => field.key === 'pan')?.source_value).toBeNull()
  })

  it('stores and deletes an application draft without caching files', () => {
    saveOfflineApplicationDraft({
      applicationId: 'MPCB-123',
      projectId: 'p1',
      approvalName: 'MPCB Consent',
      values: { company_name: 'ABC Textiles' },
      dirtyKeys: ['company_name'],
      resetFields: [],
      serverValues: { company_name: 'Old Name' },
      updatedAt: new Date().toISOString(),
      status: 'PENDING_SYNC',
    })

    expect(getOfflineApplicationDraft('MPCB-123')?.values.company_name).toBe('ABC Textiles')
    expect(countPendingOfflineDrafts()).toBe(1)
    deleteOfflineApplicationDraft('MPCB-123')
    expect(getOfflineApplicationDraft('MPCB-123')).toBeNull()
    expect(countPendingOfflineDrafts()).toBe(0)
  })

  it('caches application tracking, SLA, and readiness snapshots for low-connectivity read-only views', () => {
    cacheApplication('a1', { application_id: 'a1', approval_name: 'Factory License', status: 'UNDER_REVIEW' })
    cacheApplicationSla('a1', { status: 'AT_RISK', days_remaining: 4 })
    cacheApplicationReadiness('a1', { submission_eligible: false, blockers: ['Missing document'] })

    expect(readCachedApplication('a1')?.data.status).toBe('UNDER_REVIEW')
    expect(readCachedApplicationSla('a1')?.data.days_remaining).toBe(4)
    expect(readCachedApplicationReadiness('a1')?.data.blockers).toEqual(['Missing document'])
  })

  it('stores the approval graph separately so the offline roadmap remains meaningful', () => {
    const graph = { project_id: 'p1', nodes: [{ id: 'a1' }], edges: [{ id: 'e1' }] }
    cacheApprovalGraph('p1', graph)
    expect(readApprovalGraph('p1')?.data).toEqual(graph)
  })

  it('detects browser offline state', () => {
    Object.defineProperty(navigator, 'onLine', { configurable: true, value: false })
    expect(isOffline()).toBe(true)
  })

  it('clears all local application drafts', () => {
    const base = {
      projectId: 'p1',
      values: {},
      dirtyKeys: [],
      resetFields: [],
      serverValues: {},
      updatedAt: new Date().toISOString(),
      status: 'PENDING_SYNC' as const,
    }
    saveOfflineApplicationDraft({ ...base, applicationId: 'a1' })
    saveOfflineApplicationDraft({ ...base, applicationId: 'a2' })
    expect(countPendingOfflineDrafts()).toBe(2)
    clearAllOfflineDrafts()
    expect(countPendingOfflineDrafts()).toBe(0)
  })
})
