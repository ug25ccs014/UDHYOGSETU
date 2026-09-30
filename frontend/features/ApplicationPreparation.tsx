'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { useQueryClient } from '@tanstack/react-query'
import {
  CheckCircle2,
  FileCheck2,
  FileText,
  Loader2,
  RefreshCw,
  Save,
  ShieldCheck,
  Sparkles,
  Undo2,
  CloudOff,
  UploadCloud,
  AlertTriangle,
  GitMerge,
} from 'lucide-react'
import {
  useApplicationPreparation,
  useAttachApplicationDocument,
  useSaveApplicationPreparation,
} from '@/hooks/useApi'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import type { ApplicationPreparation as PreparationResponse, ApplicationPreparationField } from '@/types'
import { apiClient } from '@/services/api'
import { useOfflineStatus } from '@/hooks/useOfflineStatus'
import {
  cacheApplicationPreparation,
  deleteOfflineApplicationDraft,
  getOfflineApplicationDraft,
  saveOfflineApplicationDraft,
  isOfflineSensitiveField,
  type OfflineDraftRecord,
} from '@/lib/offline'

interface Props {
  applicationId: string
  compact?: boolean
}

function sourceVariant(source: string): 'info' | 'success' | 'outline' | 'warning' {
  if (source === 'USER_OVERRIDE') return 'warning'
  if (source === 'BUSINESS_PROFILE') return 'info'
  if (source === 'PROJECT') return 'success'
  if (source === 'PREPARED_SNAPSHOT') return 'warning'
  return 'outline'
}

function fieldInput(field: ApplicationPreparationField, value: any, onChange: (value: any) => void, disabled = false) {
  if (field.kind === 'textarea') {
    return (
      <textarea
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        rows={3}
        disabled={disabled}
        className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 outline-none focus:border-transparent focus:ring-2 focus:ring-blue-500"
      />
    )
  }

  if (field.kind === 'boolean') {
    return (
      <label className="mt-2 inline-flex items-center gap-3 text-sm text-gray-700">
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
          disabled={disabled}
          className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
        Yes
      </label>
    )
  }

  return (
    <Input
      type={field.kind === 'number' ? 'number' : 'text'}
      value={value ?? ''}
      onChange={(e) => onChange(field.kind === 'number' ? (e.target.value === '' ? '' : Number(e.target.value)) : e.target.value)}
      disabled={disabled}
      className="mt-1"
    />
  )
}

export function ApplicationPreparation({ applicationId, compact = false }: Props) {
  const queryClient = useQueryClient()
  const { data, isLoading, isError } = useApplicationPreparation(applicationId)
  const save = useSaveApplicationPreparation()
  const attach = useAttachApplicationDocument()
  const { isOnline } = useOfflineStatus()
  const [values, setValues] = useState<Record<string, any>>({})
  const [dirty, setDirty] = useState<Set<string>>(new Set())
  const [resetFields, setResetFields] = useState<Set<string>>(new Set())
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [attaching, setAttaching] = useState<string | null>(null)
  const [offlineDraft, setOfflineDraft] = useState<OfflineDraftRecord | null>(null)
  const [syncingOffline, setSyncingOffline] = useState(false)
  const wasOfflineRef = useRef(!isOnline)
  const restoredDraftRef = useRef(false)

  useEffect(() => {
    if (!data) return
    const initial: Record<string, any> = {}
    const serverValues: Record<string, any> = {}
    for (const field of data.fields || []) {
      initial[field.key] = field.value ?? ''
      serverValues[field.key] = field.value ?? ''
    }
    if (!data.__offlineCachedAt) cacheApplicationPreparation(data)
    const local = getOfflineApplicationDraft(applicationId)
    if (local) {
      const merged = { ...initial }
      for (const key of local.dirtyKeys) {
        if (Object.prototype.hasOwnProperty.call(local.values, key)) merged[key] = local.values[key]
      }
      setValues(merged)
      setDirty(new Set(local.dirtyKeys))
      setResetFields(new Set(local.resetFields))
      setOfflineDraft(local)
      restoredDraftRef.current = true
    } else {
      setValues(initial)
      setDirty(new Set())
      setResetFields(new Set())
      setOfflineDraft(null)
      restoredDraftRef.current = false
    }
  }, [data, applicationId])

  const sections = useMemo(() => {
    const map = new Map<string, ApplicationPreparationField[]>()
    for (const field of data?.fields || []) {
      if (!map.has(field.section)) map.set(field.section, [])
      map.get(field.section)!.push(field)
    }
    return Array.from(map.entries())
  }, [data])

  useEffect(() => {
    if (!data || !['NOT_STARTED', 'DRAFT'].includes(data.application_status)) return
    if (dirty.size === 0 && resetFields.size === 0) return
    const existing = getOfflineApplicationDraft(applicationId)
    const serverValues = existing?.serverValues || Object.fromEntries((data.fields || []).map((field) => [field.key, field.value ?? '']))
    const dirtyKeys = Array.from(dirty).filter((key) => !isOfflineSensitiveField(key))
    const resetKeys = Array.from(resetFields).filter((key) => !isOfflineSensitiveField(key))
    const blockedSensitiveKeys = Array.from(new Set([
      ...(existing?.blockedSensitiveKeys || []),
      ...Array.from(dirty).filter((key) => isOfflineSensitiveField(key)),
      ...Array.from(resetFields).filter((key) => isOfflineSensitiveField(key)),
    ]))
    if (dirtyKeys.length === 0 && resetKeys.length === 0) {
      if (blockedSensitiveKeys.length === 0) return
    }
    const draft: OfflineDraftRecord = {
      applicationId,
      projectId: data.project_id,
      approvalName: data.approval_name,
      values: Object.fromEntries(dirtyKeys.map((key) => [key, values[key]])),
      dirtyKeys,
      resetFields: resetKeys,
      serverValues: Object.fromEntries(serverValues ? Object.entries(serverValues).filter(([key]) => !isOfflineSensitiveField(key)) : []),
      updatedAt: new Date().toISOString(),
      status: existing?.status === 'CONFLICT' ? 'CONFLICT' : 'PENDING_SYNC',
      lastError: existing?.lastError,
      blockedSensitiveKeys: blockedSensitiveKeys.length > 0 ? blockedSensitiveKeys : undefined,
    }
    saveOfflineApplicationDraft(draft)
    setOfflineDraft(draft)
  }, [applicationId, data, dirty, resetFields, values])

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-10 text-sm text-gray-600">
        <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
        Building your reusable application draft...
      </div>
    )
  }

  if (isError || !data) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-sm text-gray-600">
          Application preparation is temporarily unavailable.
        </CardContent>
      </Card>
    )
  }

  const prep = data as PreparationResponse
  const readOnly = !['NOT_STARTED', 'DRAFT'].includes(prep.application_status)
  const updateValue = (key: string, value: any) => {
    setMessage('')
    setError('')
    setValues((current) => ({ ...current, [key]: value }))
    setDirty((current) => new Set(current).add(key))
    setResetFields((current) => {
      const next = new Set(current)
      next.delete(key)
      return next
    })
  }

  const resetField = (key: string) => {
    if (readOnly) return
    const field = prep.fields.find((item) => item.key === key)
    const sourceValue = field?.source_value ?? ''
    setValues((current) => ({ ...current, [key]: sourceValue }))
    setDirty((current) => new Set(current).add(key))
    setResetFields((current) => new Set(current).add(key))
  }

  const buildOfflineDraft = (): OfflineDraftRecord => {
    const dirtyKeys = Array.from(dirty).filter((key) => !isOfflineSensitiveField(key))
    const resetKeys = Array.from(resetFields).filter((key) => !isOfflineSensitiveField(key))
    const blockedSensitiveKeys = Array.from(new Set([
      ...(offlineDraft?.blockedSensitiveKeys || []),
      ...Array.from(dirty).filter((key) => isOfflineSensitiveField(key)),
      ...Array.from(resetFields).filter((key) => isOfflineSensitiveField(key)),
    ]))
    const serverValues = offlineDraft?.serverValues || Object.fromEntries(prep.fields.map((field) => [field.key, field.value ?? '']))
    return {
      applicationId,
      projectId: prep.project_id,
      approvalName: prep.approval_name,
      values: Object.fromEntries(dirtyKeys.map((key) => [key, values[key]])),
      dirtyKeys,
      resetFields: resetKeys,
      serverValues: Object.fromEntries(Object.entries(serverValues).filter(([key]) => !isOfflineSensitiveField(key))),
      updatedAt: new Date().toISOString(),
      status: offlineDraft?.status === 'CONFLICT' ? 'CONFLICT' : 'PENDING_SYNC',
      lastError: offlineDraft?.lastError,
      blockedSensitiveKeys: blockedSensitiveKeys.length > 0 ? blockedSensitiveKeys : undefined,
    }
  }

  const persistOfflineDraft = () => {
    const draft = buildOfflineDraft()
    saveOfflineApplicationDraft(draft)
    setOfflineDraft(draft)
    setMessage('Draft saved on this device. It will not be submitted to any government system while offline.')
    setError('')
  }

  const syncOfflineDraft = async (draftOverride?: OfflineDraftRecord) => {
    const draft = draftOverride || getOfflineApplicationDraft(applicationId)
    if (!draft || draft.status === 'CONFLICT' || !isOnline) return false
    setSyncingOffline(true)
    setError('')
    try {
      const latest = await apiClient.getApplicationPreparation(applicationId)
      const latestValues = Object.fromEntries((latest.fields || []).map((field: ApplicationPreparationField) => [field.key, field.value ?? '']))
      const conflicts = draft.dirtyKeys.filter((key) => {
        const baseline = draft.serverValues[key]
        const remote = latestValues[key]
        const local = draft.values[key]
        if (draft.resetFields.includes(key)) return false
        return JSON.stringify(baseline) !== JSON.stringify(remote) && JSON.stringify(local) !== JSON.stringify(remote)
      })
      if (conflicts.length > 0) {
        const conflictDraft = { ...draft, status: 'CONFLICT' as const, updatedAt: new Date().toISOString(), lastError: `Server changes detected for: ${conflicts.join(', ')}` }
        saveOfflineApplicationDraft(conflictDraft)
        setOfflineDraft(conflictDraft)
        setError('The server changed fields while you were offline. Review the conflict before syncing your edits.')
        return false
      }
      const overrides: Record<string, any> = {}
      for (const key of draft.dirtyKeys) {
        if (draft.resetFields.includes(key)) continue
        overrides[key] = draft.values[key]
      }
      const result = await save.mutateAsync({
        applicationId,
        payload: { overrides, reset_fields: draft.resetFields, mark_prepared: false },
      })
      cacheApplicationPreparation(result)
      deleteOfflineApplicationDraft(applicationId)
      setOfflineDraft(null)
      setValues(Object.fromEntries((result.fields || []).map((field: ApplicationPreparationField) => [field.key, field.value ?? ''])))
      setDirty(new Set())
      setResetFields(new Set())
      await queryClient.invalidateQueries({ queryKey: ['application-preparation', applicationId] })
      await queryClient.invalidateQueries({ queryKey: ['application-readiness', applicationId] })
      setMessage('Your offline draft was synced to the UdyogSetu server. Submission still requires a separate online action.')
      return true
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      const failed = { ...draft, status: 'PENDING_SYNC' as const, lastError: typeof detail === 'string' ? detail : 'Sync could not be completed; your local draft is preserved.' }
      saveOfflineApplicationDraft(failed)
      setOfflineDraft(failed)
      setError(failed.lastError || 'Sync could not be completed; your local draft is preserved.')
      return false
    } finally {
      setSyncingOffline(false)
    }
  }

  useEffect(() => {
    if (!isOnline) {
      wasOfflineRef.current = true
      return
    }
    if (!offlineDraft || offlineDraft.status !== 'PENDING_SYNC') return
    if (!wasOfflineRef.current && !restoredDraftRef.current) return
    wasOfflineRef.current = false
    restoredDraftRef.current = false
    void syncOfflineDraft(offlineDraft)
  }, [isOnline, offlineDraft?.applicationId, offlineDraft?.status, offlineDraft?.updatedAt])

  const discardOfflineDraft = async () => {
    deleteOfflineApplicationDraft(applicationId)
    setOfflineDraft(null)
    setDirty(new Set())
    setResetFields(new Set())
    await queryClient.invalidateQueries({ queryKey: ['application-preparation', applicationId] })
    setMessage('Local draft discarded. The server version remains unchanged.')
    setError('')
  }

  const rebaseOfflineDraft = async () => {
    if (!isOnline || !offlineDraft) return
    try {
      const latest = await apiClient.getApplicationPreparation(applicationId)
      const serverValues = Object.fromEntries((latest.fields || []).map((field: ApplicationPreparationField) => [field.key, field.value ?? '']))
      const rebased = { ...offlineDraft, serverValues, status: 'PENDING_SYNC' as const, updatedAt: new Date().toISOString(), lastError: undefined }
      saveOfflineApplicationDraft(rebased)
      setOfflineDraft(rebased)
      await syncOfflineDraft(rebased)
    } catch {
      setError('Could not refresh the server version. Your offline edits are still preserved.')
    }
  }

  const saveDraft = async (markPrepared = false) => {
    if (readOnly) return
    setMessage('')
    setError('')
    if (!isOnline) {
      if (markPrepared) {
        setError('You can save your draft offline, but marking it prepared requires an online connection.')
        return
      }
      persistOfflineDraft()
      return
    }
    try {
      const overrides: Record<string, any> = {}
      const reset_fields = Array.from(resetFields)
      for (const key of dirty) {
        if (resetFields.has(key)) continue
        const field = prep.fields.find((item) => item.key === key)
        if (!field) continue
        overrides[key] = values[key]
      }
      const result = await save.mutateAsync({
        applicationId,
        payload: { overrides, reset_fields, mark_prepared: markPrepared },
      })
      cacheApplicationPreparation(result)
      deleteOfflineApplicationDraft(applicationId)
      setOfflineDraft(null)
      setMessage(markPrepared ? 'Application preparation marked ready.' : 'Application preparation saved to the server.')
      setValues(Object.fromEntries(result.fields.map((field: ApplicationPreparationField) => [field.key, field.value ?? ''])))
      setDirty(new Set())
      setResetFields(new Set())
      await queryClient.invalidateQueries({ queryKey: ['application-preparation', applicationId] })
      await queryClient.invalidateQueries({ queryKey: ['application-readiness', applicationId] })
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      const networkFailure = !e?.response
      if (!isOnline || networkFailure) {
        persistOfflineDraft()
        return
      }
      setError(typeof detail === 'string' ? detail : detail?.message || 'Could not save application preparation.')
    }
  }

  const attachSuggested = async (documentId: string) => {
    if (readOnly) return
    setAttaching(documentId)
    setError('')
    try {
      await attach.mutateAsync({ applicationId, documentId })
      setMessage('Suggested document attached to this application.')
      queryClient.invalidateQueries({ queryKey: ['application-preparation', applicationId] })
      queryClient.invalidateQueries({ queryKey: ['application-readiness', applicationId] })
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Could not attach this document.')
    } finally {
      setAttaching(null)
    }
  }

  return (
    <div className={compact ? 'space-y-5' : 'space-y-6'}>
      <Card className="border-blue-100">
        <CardHeader className="pb-4">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="flex items-center gap-2 text-sm font-medium text-blue-700">
                <Sparkles className="h-4 w-4" />
                Applicant preparation workspace
              </div>
              <CardTitle className="mt-1 text-xl">Prepare your application</CardTitle>
              <p className="mt-1 max-w-3xl text-sm text-gray-600">
                UdyogSetu pre-fills reusable information from your Business Profile and project. Edit only what is specific to this application.
              </p>
            </div>
            <Badge variant={prep.status === 'PREPARED' ? 'success' : prep.status === 'STALE' ? 'warning' : 'outline'}>
              {prep.status === 'PREPARED' ? 'Prepared' : prep.status === 'STALE' ? 'Needs refresh' : 'Draft'}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
              <div className="text-xs text-gray-500">Required fields</div>
              <div className="mt-1 text-xl font-bold text-gray-900">{prep.summary.filled_required_fields}/{prep.summary.required_fields}</div>
            </div>
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
              <div className="text-xs text-gray-500">Preparation</div>
              <div className="mt-1 text-xl font-bold text-blue-700">{prep.summary.preparation_score}%</div>
            </div>
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
              <div className="text-xs text-gray-500">Attached docs</div>
              <div className="mt-1 text-xl font-bold text-gray-900">{prep.attached_documents.length}</div>
            </div>
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
              <div className="text-xs text-gray-500">Readiness</div>
              <div className="mt-1 text-xl font-bold text-gray-900">{prep.summary.readiness_score}%</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {(prep.__offlineCachedAt || offlineDraft) && (
        <div className={`rounded-xl border p-4 ${offlineDraft?.status === 'CONFLICT' ? 'border-red-200 bg-red-50 text-red-950' : 'border-blue-200 bg-blue-50 text-blue-950'}`}>
          <div className="flex items-start gap-3">
            {offlineDraft?.status === 'CONFLICT' ? <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-600" /> : isOnline ? <UploadCloud className="mt-0.5 h-5 w-5 shrink-0 text-blue-700" /> : <CloudOff className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" />}
            <div className="min-w-0 flex-1">
              <p className="font-semibold">{offlineDraft?.status === 'CONFLICT' ? 'Offline draft needs review' : !isOnline ? 'Working offline' : offlineDraft ? 'Draft saved locally' : 'Using locally cached application data'}</p>
              <p className="mt-1 text-sm">
                {!isOnline
                  ? 'Non-sensitive form changes are saved on this device. Sensitive identity/address fields are intentionally not persisted offline. Documents are not downloaded or stored offline, and government submission remains unavailable.'
                  : offlineDraft
                    ? 'Your local edits are preserved until they are safely synced. They will never be submitted automatically.'
                    : `This application was last cached locally${prep.__offlineCachedAt ? ` ${new Date(prep.__offlineCachedAt).toLocaleString()}` : ''}.`}
              </p>
              {offlineDraft?.lastError && <p className="mt-2 text-xs font-medium">{offlineDraft.lastError}</p>}
              {offlineDraft?.blockedSensitiveKeys?.length ? (
                <p className="mt-2 text-xs font-medium text-amber-800">
                  Sensitive fields not saved offline: {offlineDraft.blockedSensitiveKeys.join(', ')}. Re-enter or review them after reconnecting.
                </p>
              ) : null}
              {offlineDraft?.status === 'CONFLICT' && (
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button size="sm" variant="outline" onClick={() => void rebaseOfflineDraft()} disabled={syncingOffline}>
                    <GitMerge className="mr-2 h-4 w-4" /> Keep my offline edits
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => void discardOfflineDraft()}>Use server version</Button>
                </div>
              )}
              {offlineDraft?.status === 'PENDING_SYNC' && isOnline && (
                <Button size="sm" variant="outline" className="mt-3" onClick={() => void syncOfflineDraft()} disabled={syncingOffline}>
                  {syncingOffline ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <UploadCloud className="mr-2 h-4 w-4" />}
                  Sync draft now
                </Button>
              )}
            </div>
          </div>
        </div>
      )}

      {prep.status === 'STALE' && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <p className="font-semibold">Source data changed after this application was prepared.</p>
          <p className="mt-1">Review the highlighted source-backed values, then save and mark the application prepared again.</p>
          {prep.stale_fields.length > 0 && (
            <p className="mt-2 text-xs font-medium">Changed fields: {prep.stale_fields.join(' · ')}</p>
          )}
        </div>
      )}

      {readOnly && (
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
          <p className="font-semibold">Application preparation is read-only</p>
          <p className="mt-1">This application has already moved beyond draft. Preparation edits are locked after submission.</p>
        </div>
      )}

      {prep.summary.missing_required_fields.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <p className="font-semibold">Complete these before marking the application prepared:</p>
          <p className="mt-1">{prep.summary.missing_required_fields.join(' · ')}</p>
        </div>
      )}

      {message && <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">{message}</div>}
      {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>}

      <div className="space-y-5">
        {sections.map(([section, fields]) => (
          <Card key={section}>
            <CardHeader className="pb-3">
              <CardTitle className="text-base capitalize">{section}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {fields.map((field) => (
                  <div key={field.key} className="rounded-lg border border-gray-200 p-4">
                    <div className={`flex items-start justify-between gap-2 rounded-md ${field.source_changed ? 'bg-amber-50 p-2' : ''}`}>
                      <label className="text-sm font-semibold text-gray-900">
                        {field.label}
                        {field.required && <span className="ml-1 text-red-500">*</span>}
                      </label>
                      <div className="flex flex-wrap justify-end gap-1">
                        <Badge variant={sourceVariant(field.effective_source)}>{field.source_label}</Badge>
                        {field.source_changed && <Badge variant="warning">Source changed</Badge>}
                      </div>
                    </div>
                    {field.editable ? fieldInput(field, values[field.key], (value) => updateValue(field.key, value), readOnly) : (
                      <div className="mt-2 rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-700">{values[field.key] || '—'}</div>
                    )}
                    {field.source_changed && (
                      <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                        <span>Latest source value: </span>
                        <span className="font-semibold">{field.source_value ?? 'Not available'}</span>
                      </div>
                    )}
                    <div className="mt-2 flex items-center justify-between gap-2 text-xs">
                      <span className={field.status === 'MISSING' ? 'text-red-600' : 'text-gray-500'}>
                        {field.required ? (field.status === 'FILLED' ? 'Required information present' : 'Required information missing') : 'Optional'}
                      </span>
                      {field.source_changed && !readOnly ? (
                        <button
                          type="button"
                          onClick={() => resetField(field.key)}
                          className="inline-flex items-center gap-1 font-medium text-amber-700 hover:underline"
                        >
                          <RefreshCw className="h-3 w-3" /> Use latest source
                        </button>
                      ) : field.has_override && !readOnly ? (
                        <button
                          type="button"
                          onClick={() => resetField(field.key)}
                          className="inline-flex items-center gap-1 font-medium text-blue-600 hover:underline"
                        >
                          <Undo2 className="h-3 w-3" /> Reset source
                        </button>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <CardTitle className="text-base">Reusable document package</CardTitle>
              <p className="mt-1 text-sm text-gray-600">Suggested documents come from your existing project/Data Vault. Attaching them does not duplicate the file.</p>
            </div>
            <FileCheck2 className="h-5 w-5 text-blue-600" />
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {prep.attached_documents.length > 0 && (
            <div className="space-y-2">
              {prep.attached_documents.map((doc) => (
                <div key={doc.id} className="flex items-center justify-between gap-3 rounded-lg border border-green-200 bg-green-50 p-3">
                  <div className="flex min-w-0 items-center gap-3">
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-green-600" />
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-gray-900">{doc.file_name}</p>
                      <p className="text-xs text-gray-600">{doc.document_type || 'Document'} · {doc.status}</p>
                    </div>
                  </div>
                  <Badge variant="success">Attached</Badge>
                </div>
              ))}
            </div>
          )}

          {prep.recommended_documents.length > 0 ? (
            prep.recommended_documents.map((doc) => {
              const alreadyAttached = prep.attached_documents.some((attachedDoc) => attachedDoc.id === doc.document_id)
              return (
                <div key={doc.document_id} className="flex flex-col gap-3 rounded-lg border border-gray-200 p-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex min-w-0 items-start gap-3">
                    <FileText className="mt-0.5 h-4 w-4 shrink-0 text-gray-400" />
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-gray-900">{doc.file_name}</p>
                      <p className="text-xs text-gray-600">{doc.document_type || 'Document'} · {doc.status}</p>
                      <p className="mt-1 text-xs text-gray-500">Matches: {doc.requirements.join(', ')}</p>
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={readOnly || !isOnline || alreadyAttached || attaching === doc.document_id}
                    onClick={() => attachSuggested(doc.document_id)}
                  >
                    {attaching === doc.document_id ? <Loader2 className="h-4 w-4 animate-spin" /> : alreadyAttached ? 'Attached' : 'Use this document'}
                  </Button>
                </div>
              )
            })
          ) : prep.attached_documents.length === 0 ? (
            <div className="rounded-lg border border-dashed border-gray-300 p-6 text-center text-sm text-gray-600">
              <p>No reusable document suggestions are available yet.</p>
              <Link href="/dashboard/profile" className="mt-2 inline-block font-medium text-blue-600 hover:underline">Open your Data Vault →</Link>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-blue-600" />
          <div>
            <p className="text-sm font-semibold text-gray-900">Applicant-side preparation</p>
            <p className="mt-1 text-xs text-gray-600">{prep.disclaimer} No government API is contacted by this preparation workspace.</p>
          </div>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button variant="outline" disabled={save.isPending || !isOnline} onClick={() => queryClient.invalidateQueries({ queryKey: ['application-preparation', applicationId] })}>
            <RefreshCw className="mr-2 h-4 w-4" /> Refresh source data
          </Button>
          <Button onClick={() => saveDraft(false)} disabled={readOnly || save.isPending || dirty.size === 0}>
            {save.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : isOnline ? <Save className="mr-2 h-4 w-4" /> : <CloudOff className="mr-2 h-4 w-4" />}
            {isOnline ? 'Save draft' : 'Save locally'}
          </Button>
          <Button onClick={() => saveDraft(true)} disabled={readOnly || save.isPending || !isOnline || prep.summary.missing_required_fields.length > 0}>
            <CheckCircle2 className="mr-2 h-4 w-4" /> Mark prepared
          </Button>
        </div>
      </div>
    </div>
  )
}

export default ApplicationPreparation
