'use client'

import type { ApplicationPreparation, Project } from '@/types'

type CacheKind = 'project' | 'approvals' | 'approval-graph' | 'command-center' | 'applications' | 'application' | 'application-sla' | 'application-readiness' | 'application-preparation'

export interface OfflineDraftRecord {
  applicationId: string
  projectId?: string
  approvalName?: string
  values: Record<string, any>
  dirtyKeys: string[]
  resetFields: string[]
  serverValues: Record<string, any>
  updatedAt: string
  status: 'PENDING_SYNC' | 'CONFLICT'
  lastError?: string
  blockedSensitiveKeys?: string[]
}

interface CachedEnvelope<T> {
  version: 1
  savedAt: string
  data: T
}

const PREFIX = 'udyogsetu:offline:v1'
const DRAFTS_KEY = `${PREFIX}:drafts`
const CACHE_TTL_DAYS = 14

// Sensitive identity/address fields are intentionally never persisted in browser storage.
// Offline preparation remains available for non-sensitive application fields; sensitive fields
// must be completed/reviewed again after connectivity is restored.
export const OFFLINE_SENSITIVE_FIELDS = new Set([
  'pan',
  'pan_number',
  'gstin',
  'gst_number',
  'udyam',
  'udyam_number',
  'registered_address',
  'registered_address_line1',
  'registered_address_line2',
  'registered_city',
  'registered_district',
  'registered_state',
  'registered_pincode',
  'contact_person',
  'contact_name',
  'contact_email',
  'contact_phone',
])

export function isOfflineSensitiveField(key: string) {
  return OFFLINE_SENSITIVE_FIELDS.has(key.toLowerCase())
}

function sanitizeRecord(record: Record<string, any>) {
  const sanitized: Record<string, any> = {}
  for (const [key, value] of Object.entries(record)) {
    if (isOfflineSensitiveField(key)) continue
    sanitized[key] = value
  }
  return sanitized
}

function canUseStorage() {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined'
}

function userScope() {
  if (!canUseStorage()) return 'anonymous'
  try {
    const raw = window.localStorage.getItem('udyogsetu_user')
    const user = raw ? JSON.parse(raw) : null
    return String(user?.id || user?.email || 'anonymous')
  } catch {
    return 'anonymous'
  }
}

function scopedKey(kind: CacheKind, id: string) {
  return `${PREFIX}:${userScope()}:${kind}:${id}`
}

function isFresh(savedAt: string) {
  const age = Date.now() - new Date(savedAt).getTime()
  return Number.isFinite(age) && age <= CACHE_TTL_DAYS * 24 * 60 * 60 * 1000
}

function readEnvelope<T>(key: string): CachedEnvelope<T> | null {
  if (!canUseStorage()) return null
  try {
    const raw = window.localStorage.getItem(key)
    if (!raw) return null
    const envelope = JSON.parse(raw) as CachedEnvelope<T>
    if (envelope?.version !== 1 || !envelope?.savedAt || !isFresh(envelope.savedAt)) return null
    return envelope
  } catch {
    return null
  }
}

function writeEnvelope<T>(key: string, data: T) {
  if (!canUseStorage()) return false
  try {
    const envelope: CachedEnvelope<T> = {
      version: 1,
      savedAt: new Date().toISOString(),
      data,
    }
    window.localStorage.setItem(key, JSON.stringify(envelope))
    return true
  } catch {
    return false
  }
}

export function cacheProjectSummary(project: Project) {
  const safeProject = sanitizeRecord(project as Record<string, any>) as Project
  return writeEnvelope(scopedKey('project', project.id), safeProject)
}

export function readProjectSummary(projectId: string): { data: Project; savedAt: string } | null {
  const envelope = readEnvelope<Project>(scopedKey('project', projectId))
  return envelope ? { data: envelope.data, savedAt: envelope.savedAt } : null
}

export function cacheProjectApprovals(projectId: string, approvals: any[]) {
  return writeEnvelope(scopedKey('approvals', projectId), approvals)
}

export function readProjectApprovals(projectId: string): { data: any[]; savedAt: string } | null {
  const envelope = readEnvelope<any[]>(scopedKey('approvals', projectId))
  return envelope ? { data: envelope.data, savedAt: envelope.savedAt } : null
}

export function cacheApprovalGraph(projectId: string, graph: any) {
  return writeEnvelope(scopedKey('approval-graph', projectId), graph)
}

export function readApprovalGraph(projectId: string): { data: any; savedAt: string } | null {
  const envelope = readEnvelope<any>(scopedKey('approval-graph', projectId))
  return envelope ? { data: envelope.data, savedAt: envelope.savedAt } : null
}

export function cacheProjectCommandCenter(projectId: string, payload: any) {
  return writeEnvelope(scopedKey('command-center', projectId), payload)
}

export function readProjectCommandCenter(projectId: string): { data: any; savedAt: string } | null {
  const envelope = readEnvelope<any>(scopedKey('command-center', projectId))
  return envelope ? { data: envelope.data, savedAt: envelope.savedAt } : null
}

export function cacheApplications(payload: any) {
  return writeEnvelope(scopedKey('applications', 'list'), payload)
}

export function readApplications(): { data: any; savedAt: string } | null {
  const envelope = readEnvelope<any>(scopedKey('applications', 'list'))
  return envelope ? { data: envelope.data, savedAt: envelope.savedAt } : null
}

export function cacheApplication(applicationId: string, payload: any) {
  return writeEnvelope(scopedKey('application', applicationId), payload)
}

export function readCachedApplication(applicationId: string): { data: any; savedAt: string } | null {
  const envelope = readEnvelope<any>(scopedKey('application', applicationId))
  return envelope ? { data: envelope.data, savedAt: envelope.savedAt } : null
}

export function cacheApplicationSla(applicationId: string, payload: any) {
  return writeEnvelope(scopedKey('application-sla', applicationId), payload)
}

export function readCachedApplicationSla(applicationId: string): { data: any; savedAt: string } | null {
  const envelope = readEnvelope<any>(scopedKey('application-sla', applicationId))
  return envelope ? { data: envelope.data, savedAt: envelope.savedAt } : null
}

export function cacheApplicationReadiness(applicationId: string, payload: any) {
  return writeEnvelope(scopedKey('application-readiness', applicationId), payload)
}

export function readCachedApplicationReadiness(applicationId: string): { data: any; savedAt: string } | null {
  const envelope = readEnvelope<any>(scopedKey('application-readiness', applicationId))
  return envelope ? { data: envelope.data, savedAt: envelope.savedAt } : null
}

function readDraftMap(): Record<string, OfflineDraftRecord> {
  if (!canUseStorage()) return {}
  try {
    const raw = window.localStorage.getItem(`${DRAFTS_KEY}:${userScope()}`)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function writeDraftMap(map: Record<string, OfflineDraftRecord>) {
  if (!canUseStorage()) return false
  try {
    window.localStorage.setItem(`${DRAFTS_KEY}:${userScope()}`, JSON.stringify(map))
    return true
  } catch {
    return false
  }
}

export function saveOfflineApplicationDraft(draft: OfflineDraftRecord) {
  const dirtyKeys = draft.dirtyKeys.filter((key) => !isOfflineSensitiveField(key))
  const resetFields = draft.resetFields.filter((key) => !isOfflineSensitiveField(key))
  const blockedSensitiveKeys = Array.from(new Set([
    ...(draft.blockedSensitiveKeys || []),
    ...draft.dirtyKeys.filter((key) => isOfflineSensitiveField(key)),
    ...draft.resetFields.filter((key) => isOfflineSensitiveField(key)),
  ]))
  const safeDraft: OfflineDraftRecord = {
    ...draft,
    values: Object.fromEntries(dirtyKeys.map((key) => [key, draft.values[key]])),
    dirtyKeys,
    resetFields,
    serverValues: sanitizeRecord(draft.serverValues),
    blockedSensitiveKeys: blockedSensitiveKeys.length > 0 ? blockedSensitiveKeys : undefined,
  }
  const map = readDraftMap()
  map[draft.applicationId] = safeDraft
  return writeDraftMap(map)
}

export function getOfflineApplicationDraft(applicationId: string): OfflineDraftRecord | null {
  return readDraftMap()[applicationId] || null
}

export function deleteOfflineApplicationDraft(applicationId: string) {
  const map = readDraftMap()
  delete map[applicationId]
  return writeDraftMap(map)
}

export function listOfflineApplicationDrafts(): OfflineDraftRecord[] {
  return Object.values(readDraftMap()).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
}

export function countPendingOfflineDrafts() {
  return listOfflineApplicationDrafts().filter((draft) => draft.status === 'PENDING_SYNC').length
}

export function countOfflineDraftConflicts() {
  return listOfflineApplicationDrafts().filter((draft) => draft.status === 'CONFLICT').length
}

export function latestOfflineCacheTimestamp() {
  if (!canUseStorage()) return null
  const prefix = `${PREFIX}:${userScope()}:`
  let latest: string | null = null
  for (let i = 0; i < window.localStorage.length; i += 1) {
    const key = window.localStorage.key(i)
    if (!key?.startsWith(prefix)) continue
    try {
      const raw = window.localStorage.getItem(key)
      const savedAt = raw ? JSON.parse(raw)?.savedAt : null
      if (savedAt && (!latest || savedAt > latest)) latest = savedAt
    } catch {
      // Ignore malformed local cache entries.
    }
  }
  const drafts = listOfflineApplicationDrafts()
  if (drafts.length > 0) {
    const draftLatest = drafts[0].updatedAt
    if (!latest || draftLatest > latest) latest = draftLatest
  }
  return latest
}

export function clearAllOfflineDrafts() {
  const map = readDraftMap()
  if (Object.keys(map).length === 0) return true
  return writeDraftMap({})
}

export function isOffline() {
  return typeof navigator !== 'undefined' && navigator.onLine === false
}

export function formatOfflineTimestamp(timestamp?: string | null) {
  if (!timestamp) return null
  try {
    return new Date(timestamp).toLocaleString()
  } catch {
    return timestamp
  }
}

export type CachedApplicationPreparation = Pick<ApplicationPreparation, 'application_id' | 'approval_id' | 'approval_name' | 'department' | 'project_id' | 'project_name' | 'application_status' | 'status' | 'stale_fields' | 'summary' | 'fields' | 'attached_documents' | 'recommended_documents' | 'sources' | 'disclaimer'>

export function cacheApplicationPreparation(data: CachedApplicationPreparation) {
  const safeFields = (data.fields || []).map((field) => {
    if (!isOfflineSensitiveField(field.key)) return field
    return { ...field, value: null, source_value: null }
  })
  const safeData: CachedApplicationPreparation = { ...data, fields: safeFields }
  return writeEnvelope(scopedKey('application-preparation', data.application_id), safeData)
}

export function readCachedApplicationPreparation(applicationId: string): { data: CachedApplicationPreparation; savedAt: string } | null {
  const envelope = readEnvelope<CachedApplicationPreparation>(scopedKey('application-preparation', applicationId))
  return envelope ? { data: envelope.data, savedAt: envelope.savedAt } : null
}
