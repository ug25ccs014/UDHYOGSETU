'use client'

import { useLanguage } from '@/lib/language'
import PageHeader from '@/components/PageHeader'
import { useMemo, useState, type ReactNode } from 'react'
import { useParams, useRouter } from 'next/navigation'
import {
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  FileCheck2,
  Loader2,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
} from 'lucide-react'
import {
  useBusinessProfileDocuments,
  useCompleteComplianceItem,
  useComplianceDashboard,
  usePrepareRenewal,
  useUpdateRenewal,
} from '@/hooks/useApi'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import type { ComplianceLifecycleItem, RenewalCase } from '@/types'

function statusBadge(status: string): 'success' | 'warning' | 'danger' | 'info' | 'outline' {
  if (status === 'ON_TRACK') return 'success'
  if (status === 'AT_RISK') return 'warning'
  if (status === 'OVERDUE') return 'danger'
  return 'outline'
}

function renewalBadge(status: string): 'success' | 'warning' | 'danger' | 'default' | 'info' {
  if (status === 'RENEWED') return 'success'
  if (status === 'OVERDUE') return 'danger'
  if (status === 'DUE_SOON') return 'warning'
  if (status === 'IN_PROGRESS' || status === 'PREPARING' || status === 'READY_FOR_SUBMISSION') return 'info'
  return 'default'
}

function formatDate(value?: string | null) {
  if (!value) return '—'
  return new Date(value).toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' })
}

function formatDue(days?: number | null) {
  if (days == null) return 'No due date'
  if (days < 0) return `${Math.abs(days)} days overdue`
  if (days === 0) return 'Due today'
  return `Due in ${days} days`
}

function lifecycleLabel(status: string) {
  return status.split('_').join(' ')
}

export default function ProjectCompliancePage() {
  const { t } = useLanguage()
  const params = useParams()
  const router = useRouter()
  const projectId = params.projectId as string
  const dashboard = useComplianceDashboard(projectId)
  const vault = useBusinessProfileDocuments()
  const completeItem = useCompleteComplianceItem()
  const prepareRenewal = usePrepareRenewal()
  const updateRenewal = useUpdateRenewal()
  const [selectedRenewal, setSelectedRenewal] = useState<RenewalCase | null>(null)
  const [message, setMessage] = useState('')
  const [filter, setFilter] = useState('ALL')

  const items: ComplianceLifecycleItem[] = useMemo(() => dashboard.data?.items || [], [dashboard.data?.items])
  const renewals: RenewalCase[] = dashboard.data?.renewals || []

  const filteredItems = useMemo(() => {
    if (filter === 'ALL') return items
    return items.filter((item) => item.status === filter)
  }, [filter, items])

  const complete = async (item: ComplianceLifecycleItem) => {
    setMessage('')
    try {
      await completeItem.mutateAsync({ itemId: item.id })
      setMessage(`Completed: ${item.requirement}`)
      await dashboard.refetch()
    } catch (error: any) {
      setMessage(error.response?.data?.detail || 'Could not complete this task.')
    }
  }

  const viewRenewal = async (renewal: RenewalCase) => {
    setMessage('')
    if (!renewal.case_id) return
    try {
      const { apiClient } = await import('@/services/api')
      const result = await apiClient.getRenewal(renewal.case_id)
      setSelectedRenewal(result)
    } catch (error: any) {
      setMessage(error.response?.data?.detail || 'Could not load renewal case.')
    }
  }

  const startRenewal = async (renewal: RenewalCase) => {
    setMessage('')
    try {
      const result = await prepareRenewal.mutateAsync({ projectId, approvalId: renewal.approval_id })
      setSelectedRenewal(result)
      setMessage('Renewal preparation started. The original approval remains unchanged.')
      await dashboard.refetch()
    } catch (error: any) {
      setMessage(error.response?.data?.detail || 'Could not start renewal preparation.')
    }
  }

  const markReady = async () => {
    if (!selectedRenewal?.id) return
    try {
      const result = await updateRenewal.mutateAsync({
        renewalId: selectedRenewal.id,
        payload: { status: 'READY_FOR_SUBMISSION' },
      })
      setSelectedRenewal(result)
      setMessage('Renewal pack is marked ready for external submission.')
      await dashboard.refetch()
    } catch (error: any) {
      setMessage(error.response?.data?.detail || 'Could not mark renewal ready.')
    }
  }

  const markSubmittedExternally = async (reference: string) => {
    if (!selectedRenewal?.id) return
    try {
      const result = await updateRenewal.mutateAsync({
        renewalId: selectedRenewal.id,
        payload: {
          status: 'SUBMITTED_EXTERNALLY',
          external_reference: reference || undefined,
        },
      })
      setSelectedRenewal(result)
      setMessage('Renewal is recorded as applicant-reported external submission. No government API call was made.')
      await dashboard.refetch()
    } catch (error: any) {
      setMessage(error.response?.data?.detail || 'Could not record external submission.')
    }
  }

  const markRenewed = async () => {
    if (!selectedRenewal?.id) return
    try {
      const result = await updateRenewal.mutateAsync({
        renewalId: selectedRenewal.id,
        payload: { status: 'RENEWED' },
      })
      setSelectedRenewal(result)
      setMessage('Renewal marked renewed in UDYOGSETU.')
      await dashboard.refetch()
    } catch (error: any) {
      setMessage(error.response?.data?.detail || 'Could not mark renewal as renewed.')
    }
  }

  if (dashboard.isLoading) {
    return <div className="text-center py-24 text-gray-600">Loading compliance lifecycle…</div>
  }

  if (dashboard.isError || !dashboard.data) {
    return (
      <div className="text-center py-24">
        <p className="text-lg text-gray-900">Compliance data unavailable</p>
        <p className="mt-2 text-gray-600">Run the approval analysis first to generate compliance requirements.</p>
        <Button className="mt-6" onClick={() => router.push(`/dashboard/${projectId}/approvals`)}>Go to Approvals</Button>
      </div>
    )
  }

  const summary = dashboard.data.summary || {}
  const attentionCount = Number(summary.at_risk || 0) + Number(summary.overdue || 0)

  return (
    <div className="space-y-8">
      <PageHeader
        icon={ShieldCheck}
        title={t('pg.complTitle')}
        purpose={t('pg.complPurpose')}
        action={
          <Button variant="outline" onClick={() => dashboard.refetch()} disabled={dashboard.isFetching}>
            {dashboard.isFetching ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            {t('pg.refresh')}
          </Button>
        }
      />

      {message && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">{message}</div>
      )}

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-5">
        <Metric label="Compliance score" value={`${dashboard.data.score ?? 0}%`} icon={<CheckCircle2 className="w-5 h-5" />} tone="green" />
        <Metric label="On track" value={summary.on_track ?? 0} icon={<CheckCircle2 className="w-5 h-5" />} tone="green" />
        <Metric label="At risk" value={summary.at_risk ?? 0} icon={<AlertTriangle className="w-5 h-5" />} tone="amber" />
        <Metric label="Overdue" value={summary.overdue ?? 0} icon={<Clock3 className="w-5 h-5" />} tone="red" />
        <Metric label="Renewals needing review" value={summary.renewals_due ?? 0} icon={<CalendarClock className="w-5 h-5" />} tone="violet" />
      </div>

      <Card className={attentionCount > 0 ? 'border-amber-200' : ''}>
        <CardHeader className="pb-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Compliance task list</CardTitle>
              <p className="mt-1 text-sm text-gray-500">Complete recurring tasks to reset their next due date using the configured cadence.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {['ALL', 'ON_TRACK', 'AT_RISK', 'OVERDUE'].map((value) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setFilter(value)}
                  className={`rounded-full border px-3.5 py-1.5 text-xs font-bold transition ${filter === value ? 'border-navy bg-navy text-cream' : 'border-gray-200 bg-white text-gray-600 hover:border-blue-300'}`}
                >
                  {lifecycleLabel(value)}
                </button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredItems.length === 0 ? (
            <div className="py-12 text-center text-sm text-gray-500">No compliance tasks match this filter.</div>
          ) : (
            <div className="space-y-3">
              {filteredItems.map((item) => (
                <div key={item.id} className="rounded-xl border border-gray-200 p-4">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-gray-900">{item.requirement}</p>
                        <Badge variant={statusBadge(item.status)}>{lifecycleLabel(item.status)}</Badge>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
                        <span>{item.category}</span>
                        <span>{item.frequency || 'Configured cadence'}</span>
                        <span>{formatDue(item.days_until_due)}</span>
                        <span>Next due {formatDate(item.next_due)}</span>
                        {item.last_completed && <span>Last completed {formatDate(item.last_completed)}</span>}
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant={item.status === 'OVERDUE' ? 'default' : 'outline'}
                      onClick={() => complete(item)}
                      disabled={completeItem.isPending || !item.can_complete}
                    >
                      {completeItem.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <ClipboardCheck className="w-4 h-4 mr-2" />}
                      Mark completed
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div>
              <CardTitle>Renewal lifecycle</CardTitle>
              <p className="mt-1 text-sm text-gray-500">Prepare renewal packs before the renewal window, while keeping the original approval record intact.</p>
            </div>
            <RotateCcw className="w-6 h-6 text-violet-700" />
          </div>
        </CardHeader>
        <CardContent>
          {renewals.length === 0 ? (
            <div className="rounded-xl border border-dashed border-gray-200 p-10 text-center text-sm text-gray-500">No renewable approved approvals are currently configured for this project.</div>
          ) : (
            <div className="space-y-3">
              {renewals.map((renewal) => (
                <div key={renewal.approval_id} className="rounded-xl border border-gray-200 p-4">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-gray-900">{renewal.approval_name}</p>
                        <Badge variant={renewalBadge(renewal.lifecycle_status)}>{lifecycleLabel(renewal.lifecycle_status)}</Badge>
                      </div>
                      <div className="mt-2 grid grid-cols-1 sm:grid-cols-3 gap-x-6 gap-y-1 text-xs text-gray-500">
                        <span>{renewal.department}</span>
                        <span>Renewal date {formatDate(renewal.renewal_date)}</span>
                        <span>{renewal.days_until_renewal < 0 ? `${Math.abs(renewal.days_until_renewal)} days overdue` : `${renewal.days_until_renewal} days remaining`}</span>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {renewal.case_id && <Button size="sm" variant="outline" onClick={() => viewRenewal(renewal)}>View case</Button>}
                      {renewal.can_prepare && !renewal.case_id && (
                        <Button size="sm" onClick={() => startRenewal(renewal)} disabled={prepareRenewal.isPending}>
                          {prepareRenewal.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileCheck2 className="w-4 h-4 mr-2" />}
                          Prepare renewal
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {selectedRenewal?.id && (
        <RenewalCasePanel
          renewal={selectedRenewal}
          projectId={projectId}
          vaultDocuments={vault.data?.documents || vault.data || []}
          updateRenewal={updateRenewal}
          onUpdate={setSelectedRenewal}
          onMessage={setMessage}
          onReady={markReady}
          onSubmitExternally={(reference: string) => markSubmittedExternally(reference)}
          onRenewed={markRenewed}
        />
      )}

      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs leading-5 text-slate-600">
        <span className="font-semibold text-slate-800">Transparency:</span> compliance cadences and renewal dates come from the configured UDYOGSETU rules/records. They are operational guidance, not government guarantees. Renewal status marked <span className="font-semibold">SUBMITTED EXTERNALLY</span> is applicant-reported; this prototype does not call a government renewal API.
      </div>
    </div>
  )
}

function Metric({ label, value, icon, tone }: { label: string; value: string | number; icon: ReactNode; tone: 'green' | 'amber' | 'red' | 'violet' }) {
  const styles = {
    green: 'bg-teal-100 text-teal-700',
    amber: 'bg-sun/30 text-navy-ink',
    red: 'bg-coral/20 text-coral',
    violet: 'bg-blue-100 text-blue-600',
  }[tone]
  return (
    <div className="rounded-2xl border border-gray-200 bg-white/90 p-5 shadow-card transition duration-200 hover:-translate-y-0.5 hover:shadow-soft">
      <div className={`grid h-11 w-11 place-items-center rounded-xl ${styles}`}>{icon}</div>
      <p className="mt-4 text-sm font-semibold text-gray-600">{label}</p>
      <p className="mt-0.5 text-3xl font-extrabold tracking-tight text-navy">{value}</p>
    </div>
  )
}

function RenewalCasePanel({ renewal, vaultDocuments, updateRenewal, onUpdate, onMessage, onReady, onSubmitExternally, onRenewed }: any) {
  const [selectedDocs, setSelectedDocs] = useState<string[]>(renewal.documents?.map((doc: any) => doc.id) || [])
  const [notes, setNotes] = useState(renewal.notes || '')
  const [reference, setReference] = useState(renewal.external_reference || '')
  const isPreparing = renewal.status === 'PREPARING'
  const selected = new Set(selectedDocs)

  const savePackage = async () => {
    try {
      const result = await updateRenewal.mutateAsync({
        renewalId: renewal.id,
        payload: { document_ids: selectedDocs, notes },
      })
      onUpdate(result)
      onMessage('Renewal package updated.')
    } catch (error: any) {
      onMessage(error.response?.data?.detail || 'Could not update renewal package.')
    }
  }

  return (
    <Card className="border-violet-200 shadow-sm">
      <CardHeader>
        <CardTitle>Renewal case — {renewal.approval_name}</CardTitle>
        <p className="text-sm text-gray-500">This case prepares the next renewal without mutating the original approval.</p>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <Info label="Status" value={lifecycleLabel(renewal.status)} />
          <Info label="Documents ready" value={`${renewal.document_readiness?.available_count ?? 0} / ${renewal.document_readiness?.required_count ?? 0}`} />
          <Info label="Original approval" value={renewal.approval_name} />
        </div>

        {renewal.document_readiness?.missing?.length > 0 && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            <p className="font-semibold">Documents to review</p>
            <ul className="mt-2 space-y-1 list-disc pl-5">{renewal.document_readiness.missing.map((item: string) => <li key={item}>{item}</li>)}</ul>
          </div>
        )}

        {isPreparing && vaultDocuments.length > 0 && (
          <div>
            <p className="text-sm font-semibold text-gray-900">Select reusable project documents</p>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {vaultDocuments.map((doc: any) => (
                <label key={doc.id} className="flex items-center gap-3 rounded-xl border border-gray-200 p-3 text-sm">
                  <input
                    type="checkbox"
                    checked={selected.has(doc.id)}
                    onChange={() => setSelectedDocs((current) => current.includes(doc.id) ? current.filter((id) => id !== doc.id) : [...current, doc.id])}
                  />
                  <span className="min-w-0"><span className="block font-medium text-gray-900 truncate">{doc.file_name}</span><span className="block text-xs text-gray-500">{doc.document_type || doc.status}</span></span>
                </label>
              ))}
            </div>
          </div>
        )}

        <div>
          <label className="text-sm font-semibold text-gray-900">Case notes</label>
          <textarea value={notes} onChange={(event) => setNotes(event.target.value)} disabled={!isPreparing} className="mt-2 w-full min-h-24 rounded-xl border border-gray-300 px-3 py-2 text-sm" placeholder="Record preparation notes, external instructions, or evidence references." />
        </div>

        {renewal.status === 'READY_FOR_SUBMISSION' && (
          <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">The renewal pack is ready. Submission happens through the relevant external process unless an authorized UDYOGSETU government integration exists.</div>
        )}

        {renewal.status === 'SUBMITTED_EXTERNALLY' && (
          <div className="rounded-xl border border-teal-100 bg-teal-50 p-4 text-sm text-teal-700">Recorded as externally submitted. Reference: {renewal.external_reference || 'Not provided'}.</div>
        )}

        {renewal.status === 'PREPARING' && (
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={savePackage} disabled={updateRenewal.isPending}><RefreshCw className="w-4 h-4 mr-2" />Save package</Button>
            <Button onClick={onReady} disabled={updateRenewal.isPending || !renewal.can_mark_ready}><FileCheck2 className="w-4 h-4 mr-2" />Mark ready</Button>
          </div>
        )}

        {renewal.status === 'READY_FOR_SUBMISSION' && (
          <div className="flex flex-wrap gap-2">
            <input value={reference} onChange={(event) => setReference(event.target.value)} className="h-9 rounded-lg border border-gray-300 px-3 text-sm" placeholder="External reference (optional)" />
            <Button onClick={onSubmitExternally} disabled={updateRenewal.isPending}>Record external submission</Button>
          </div>
        )}

        {renewal.status === 'SUBMITTED_EXTERNALLY' && (
          <Button onClick={onRenewed} disabled={updateRenewal.isPending}>Mark renewed</Button>
        )}

        <p className="text-[11px] leading-4 text-gray-500">No government API is called by these case actions. “External submission” records an applicant-reported event only.</p>
      </CardContent>
    </Card>
  )
}

function Info({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl bg-gray-50 p-3"><p className="text-[11px] uppercase tracking-wide text-gray-400">{label}</p><p className="mt-1 text-sm font-medium text-gray-900">{value}</p></div>
}
