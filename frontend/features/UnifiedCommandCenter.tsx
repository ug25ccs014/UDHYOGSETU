'use client'

import { useMemo, useState, type ElementType, type ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import {
  AlertTriangle,
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  Clock3,
  FileCheck2,
  FileWarning,
  Gift,
  GitBranch,
  LifeBuoy,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  FlaskConical,
  UserRound,
} from 'lucide-react'
import { useProjectCommandCenter } from '@/hooks/useApi'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { CommandCenterApproval } from '@/types'

interface Props {
  projectId: string
}

function formatDate(value?: string | null, withTime = false) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return withTime
    ? date.toLocaleString([], { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
    : date.toLocaleDateString([], { day: '2-digit', month: 'short', year: 'numeric' })
}

function daysLabel(value?: number | null) {
  if (value === null || value === undefined) return '—'
  const rounded = Math.round(value * 10) / 10
  return `${rounded} day${rounded === 1 ? '' : 's'}`
}

function statusBadge(status: string) {
  switch (status) {
    case 'APPROVED':
      return { label: 'Approved', variant: 'success' as const }
    case 'QUERY_RAISED':
      return { label: 'Query raised', variant: 'warning' as const }
    case 'INSPECTION':
      return { label: 'Inspection', variant: 'info' as const }
    case 'UNDER_REVIEW':
      return { label: 'Under review', variant: 'default' as const }
    case 'SUBMITTED':
      return { label: 'Submitted', variant: 'default' as const }
    case 'REJECTED':
      return { label: 'Rejected', variant: 'danger' as const }
    case 'EXPIRED':
      return { label: 'Expired', variant: 'warning' as const }
    case 'DRAFT':
      return { label: 'Draft', variant: 'outline' as const }
    case 'NOT_STARTED':
      return { label: 'Not started', variant: 'outline' as const }
    default:
      return { label: status.replaceAll('_', ' '), variant: 'outline' as const }
  }
}

function priorityClasses(priority: string) {
  switch (priority) {
    case 'HIGH':
      return 'border-red-200 bg-red-50 text-red-900'
    case 'MEDIUM':
      return 'border-amber-200 bg-amber-50 text-amber-900'
    default:
      return 'border-blue-200 bg-blue-50 text-blue-900'
  }
}

function progressWidth(value: number, total: number) {
  if (!total || total <= 0) return 0
  return Math.max(0, Math.min(100, (value / total) * 100))
}

function ApprovalCard({ approval, onOpen }: { approval: CommandCenterApproval; onOpen: () => void }) {
  const status = statusBadge(approval.status)
  const risk = approval.risk.band
  const slaStatus = approval.sla.status
  const riskClass = risk === 'HIGH' ? 'text-red-700' : risk === 'MEDIUM' ? 'text-amber-700' : 'text-slate-600'
  const hasAttention = approval.action.priority !== 'NONE'

  return (
    <div className={`rounded-xl border p-4 ${hasAttention ? 'border-slate-300 bg-white' : 'border-gray-200 bg-white'}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-semibold text-gray-950 truncate">{approval.name}</h3>
            {approval.mandatory && <Badge variant="outline">Mandatory</Badge>}
          </div>
          <p className="mt-1 text-xs text-gray-500">{approval.department}</p>
        </div>
        <Badge variant={status.variant}>{status.label}</Badge>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-lg bg-gray-50 p-2.5">
          <p className="text-gray-500">SLA</p>
          <p className="mt-1 font-semibold text-gray-900">{slaStatus || '—'}</p>
          {approval.sla.days_remaining !== null && approval.sla.days_remaining !== undefined && (
            <p className="mt-0.5 text-gray-500">{daysLabel(approval.sla.days_remaining)} remaining</p>
          )}
        </div>
        <div className="rounded-lg bg-gray-50 p-2.5">
          <p className="text-gray-500">Risk</p>
          <p className={`mt-1 font-semibold ${riskClass}`}>{risk || '—'}</p>
          {approval.risk.score !== null && approval.risk.score !== undefined && (
            <p className="mt-0.5 text-gray-500">Score {approval.risk.score}</p>
          )}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-2 text-xs">
        {approval.query.open_count > 0 && <Badge variant="warning">{approval.query.open_count} query</Badge>}
        {approval.inspection.scheduled && <Badge variant="info">Inspection scheduled</Badge>}
        {approval.renewal && <Badge variant="outline">Renewal due</Badge>}
        {approval.readiness.state === 'BLOCKED' && <Badge variant="danger">Submission blocked</Badge>}
        {approval.readiness.state === 'ACTION_REQUIRED' && <Badge variant="warning">Readiness action</Badge>}
      </div>

      {approval.action.label && (
        <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
          <span className="font-semibold">Next:</span> {approval.action.label}
        </div>
      )}

      <Button variant="ghost" size="sm" className="mt-3 px-0 text-blue-700 hover:bg-transparent hover:text-blue-800" onClick={onOpen}>
        Open application <ArrowRight className="ml-1 h-4 w-4" />
      </Button>
    </div>
  )
}

export function UnifiedCommandCenter({ projectId }: Props) {
  const router = useRouter()
  const { data, isLoading, isError, refetch, isFetching } = useProjectCommandCenter(projectId)
  const [filter, setFilter] = useState('ALL')

  const filteredApprovals = useMemo(() => {
    const approvals = data?.approvals ?? []
    if (filter === 'ALL') return approvals
    if (filter === 'ACTION') return approvals.filter((a) => a.action.priority !== 'NONE')
    if (filter === 'APPROVED') return approvals.filter((a) => a.status === 'APPROVED')
    if (filter === 'IN_PROGRESS') return approvals.filter((a) => ['SUBMITTED', 'UNDER_REVIEW', 'INSPECTION', 'QUERY_RAISED'].includes(a.status))
    return approvals.filter((a) => a.status === filter)
  }, [data?.approvals, filter])

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-36 rounded-2xl bg-gray-200" />
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {[1, 2, 3, 4].map((item) => <div key={item} className="h-28 rounded-xl bg-gray-200" />)}
        </div>
        <div className="h-56 rounded-2xl bg-gray-200" />
      </div>
    )
  }

  if (isError || !data) {
    return (
      <Card>
        <CardContent className="py-16 text-center">
          <ShieldAlert className="mx-auto h-10 w-10 text-amber-500" />
          <p className="mt-4 text-lg font-semibold text-gray-900">Command Center unavailable</p>
          <p className="mt-1 text-sm text-gray-600">We could not load this project’s unified operating view.</p>
          <Button className="mt-5" onClick={() => refetch()}>Try again</Button>
        </CardContent>
      </Card>
    )
  }

  const overview = data.overview
  const profile = data.profile
  const actionCenter = data.action_center ?? []
  const approvalTotal = Math.max(overview.approval_count, 1)
  const completionPct = progressWidth(overview.approved, approvalTotal)
  const documentPct = progressWidth(data.documents.ready, Math.max(data.documents.total, 1))
  const compliancePct = Math.max(0, Math.min(100, Number(data.compliance.score || 0)))
  const criticalPath = data.roadmap.critical_path_names ?? []

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="default">Unified Command Center</Badge>
              <Badge variant="outline">Prototype data</Badge>
              {data.__offlineCachedAt && <Badge variant="warning">Offline cache</Badge>}
              <button
                type="button"
                onClick={() => refetch()}
                className="inline-flex items-center gap-1 rounded-full border border-gray-200 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50"
                disabled={isFetching}
              >
                <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} />
                Refresh
              </button>
              <Button
                size="sm"
                variant="outline"
                className="rounded-full"
                onClick={() => router.push(`/dashboard/${projectId}/simulate`)}
              >
                <FlaskConical className="mr-1.5 h-3.5 w-3.5" />
                Simulate scenario
              </Button>
            </div>
            <h1 className="mt-3 text-2xl font-bold tracking-tight text-gray-950 sm:text-3xl">{data.project.name}</h1>
            <p className="mt-1 text-gray-600">{data.project.company_name} · {data.project.location || 'Location not specified'}</p>
            <p className="mt-1 text-xs text-gray-500">{data.project.industry || 'Industry'} · {data.project.project_stage || 'Project stage not specified'}</p>
            {data.__offlineCachedAt && <p className="mt-1 text-xs text-amber-700">Showing the latest locally cached command-center snapshot. Refresh when online for live application data.</p>}
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 lg:min-w-[250px]">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Operational readiness</p>
            <div className="mt-2 flex items-end justify-between gap-3">
              <span className="text-4xl font-bold text-slate-950">{overview.project_readiness_score}%</span>
              <span className="text-xs text-slate-500">Advisory view</span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200">
              <div className="h-full rounded-full bg-slate-700 transition-all" style={{ width: `${overview.project_readiness_score}%` }} />
            </div>
            <p className="mt-2 text-[11px] leading-4 text-slate-500">Composite operational indicator. It is not a statutory or government score.</p>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-8">
        {[
          ['Approvals', overview.approval_count, FileCheck2, 'text-blue-700'],
          ['Approved', overview.approved, CheckCircle2, 'text-green-700'],
          ['In progress', overview.in_progress, Clock3, 'text-slate-700'],
          ['Action needed', overview.action_count, AlertTriangle, 'text-amber-700'],
          ['Queries', overview.queries, LifeBuoy, 'text-orange-700'],
          ['High risk', overview.high_risk, ShieldAlert, 'text-red-700'],
          ['Renewals', overview.renewals_due, RefreshCw, 'text-violet-700'],
          ['Incentives', overview.incentive_matches, Gift, 'text-emerald-700'],
        ].map(([label, value, Icon, iconClass]) => {
          const I = Icon as ElementType
          return (
            <Card key={String(label)} className="shadow-none">
              <CardContent className="p-3.5 sm:p-4">
                <I className={`h-4 w-4 ${iconClass}`} />
                <p className="mt-2 text-[11px] font-medium uppercase tracking-wide text-gray-500">{label}</p>
                <p className="mt-1 text-2xl font-bold text-gray-950">{value}</p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <section className="grid gap-6 lg:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.75fr)]">
        <Card>
          <CardHeader className="pb-3">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle>Action Center</CardTitle>
                <p className="mt-1 text-sm text-gray-500">The most important things requiring attention right now.</p>
              </div>
              <Badge variant={actionCenter.length ? 'warning' : 'success'}>{actionCenter.length} action{actionCenter.length === 1 ? '' : 's'}</Badge>
            </div>
          </CardHeader>
          <CardContent>
            {actionCenter.length === 0 ? (
              <div className="rounded-xl border border-green-200 bg-green-50 p-5 text-center">
                <CheckCircle2 className="mx-auto h-7 w-7 text-green-700" />
                <p className="mt-2 font-semibold text-green-900">No immediate action required</p>
                <p className="mt-1 text-sm text-green-800">Continue routine monitoring across the project domains.</p>
              </div>
            ) : (
              <div className="space-y-2.5">
                {actionCenter.map((action) => (
                  <button
                    key={action.id}
                    type="button"
                    onClick={() => router.push(action.target)}
                    className={`w-full rounded-xl border p-3.5 text-left transition hover:-translate-y-0.5 hover:shadow-sm ${priorityClasses(action.priority)}`}
                  >
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5">
                        {action.priority === 'HIGH' ? <AlertTriangle className="h-4 w-4" /> : action.priority === 'MEDIUM' ? <Clock3 className="h-4 w-4" /> : <ArrowRight className="h-4 w-4" />}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="font-semibold">{action.title}</p>
                          <span className="text-[10px] font-bold uppercase tracking-wide opacity-70">{action.priority}</span>
                        </div>
                        <p className="mt-1 text-sm leading-5 opacity-90">{action.description}</p>
                      </div>
                      <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 opacity-60" />
                    </div>
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-3"><CardTitle>Readiness Snapshot</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <MetricBar label="Business Profile" value={profile.completeness_score} trailing={`${profile.identity_fields_present}/3 identities`} />
              <MetricBar label="Approved approvals" value={completionPct} trailing={`${overview.approved}/${overview.approval_count}`} />
              <MetricBar label="Verified documents" value={documentPct} trailing={`${data.documents.ready}/${data.documents.total}`} />
              <MetricBar label="Compliance" value={compliancePct} trailing={`${data.compliance.overdue} overdue`} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3"><CardTitle>Journey Estimate</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-3">
                <MetricTile label="Parallel journey" value={daysLabel(data.roadmap.parallel_duration_days)} />
                <MetricTile label="Sequential" value={daysLabel(data.roadmap.sequential_duration_days)} />
                <MetricTile label="Estimated saved" value={daysLabel(data.roadmap.time_saved_days)} emphasis />
                <MetricTile label="Critical path" value={daysLabel(data.roadmap.critical_path_days)} />
              </div>
              {criticalPath.length > 0 && (
                <div className="mt-4 rounded-lg border border-yellow-200 bg-yellow-50 p-3 text-xs text-yellow-950">
                  <div className="flex items-start gap-2">
                    <GitBranch className="mt-0.5 h-4 w-4 shrink-0" />
                    <span><span className="font-semibold">Critical path:</span> {criticalPath.join(' → ')}</span>
                  </div>
                </div>
              )}
              <p className="mt-3 text-[11px] leading-4 text-gray-500">Durations are configured estimates used for planning. They are not government service guarantees.</p>
            </CardContent>
          </Card>
        </div>
      </section>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <CardTitle>Approval Portfolio</CardTitle>
              <p className="mt-1 text-sm text-gray-500">Every approval, its current state, risk, SLA, readiness and next action.</p>
            </div>
            <div className="relative">
              <select value={filter} onChange={(event) => setFilter(event.target.value)} className="h-9 appearance-none rounded-lg border border-gray-200 bg-white pl-3 pr-9 text-sm text-gray-700 outline-none focus:border-blue-400">
                <option value="ALL">All approvals</option>
                <option value="ACTION">Needs action</option>
                <option value="IN_PROGRESS">In progress</option>
                <option value="APPROVED">Approved</option>
                <option value="QUERY_RAISED">Query raised</option>
                <option value="INSPECTION">Inspection</option>
                <option value="DRAFT">Draft</option>
              </select>
              <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredApprovals.length === 0 ? (
            <div className="rounded-xl border border-dashed border-gray-200 p-10 text-center text-sm text-gray-500">No approvals match this view.</div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {filteredApprovals.map((approval) => (
                <ApprovalCard
                  key={approval.id}
                  approval={approval}
                  onOpen={() => router.push(`/dashboard/applications/${encodeURIComponent(approval.application_id)}`)}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <section className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader className="pb-3"><CardTitle>Compliance & Renewals</CardTitle></CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-3xl font-bold text-gray-950">{data.compliance.score}%</p>
                <p className="mt-1 text-sm text-gray-500">Compliance score</p>
              </div>
              <ShieldCheck className="h-8 w-8 text-green-700" />
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
              <Stat label="On track" value={data.compliance.on_track} />
              <Stat label="At risk" value={data.compliance.at_risk} />
              <Stat label="Overdue" value={data.compliance.overdue} danger />
            </div>
            {data.compliance.renewals.length > 0 && (
              <Button variant="outline" className="mt-4 w-full" onClick={() => router.push(`/dashboard/${projectId}/compliance`)}>Review renewals</Button>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3"><CardTitle>Upcoming Inspections</CardTitle></CardHeader>
          <CardContent>
            {data.inspections.upcoming.length === 0 ? (
              <EmptyState icon={<CalendarDays className="h-6 w-6" />} text="No scheduled inspections." />
            ) : (
              <div className="space-y-3">
                {data.inspections.upcoming.slice(0, 3).map((visit: any) => (
                  <div key={visit.visit_id} className="rounded-lg border border-gray-200 p-3">
                    <p className="font-semibold text-gray-900">{formatDate(visit.scheduled_start, true)}</p>
                    <p className="mt-1 text-xs text-gray-500">{visit.location || 'Location not specified'}</p>
                    <Badge className="mt-2" variant="info">Scheduled</Badge>
                  </div>
                ))}
                <Button variant="outline" className="w-full" onClick={() => router.push('/dashboard/inspections')}>Open inspection planner</Button>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3"><CardTitle>Schemes & Support</CardTitle></CardHeader>
          <CardContent>
            {data.incentives.top_matches.length === 0 ? (
              <EmptyState icon={<Gift className="h-6 w-6" />} text="No configured catalogue matches yet." />
            ) : (
              <div className="space-y-3">
                {data.incentives.top_matches.slice(0, 3).map((match) => (
                  <div key={match.id} className="rounded-lg border border-gray-200 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <p className="font-semibold text-gray-900">{match.name}</p>
                      <Badge variant="success">{match.match_score ?? 0}%</Badge>
                    </div>
                    <p className="mt-1 text-xs text-gray-500 line-clamp-2">{match.match_reason || 'Matched from the configured project profile.'}</p>
                  </div>
                ))}
                <Button variant="outline" className="w-full" onClick={() => router.push(`/dashboard/${projectId}/schemes`)}>View schemes</Button>
              </div>
            )}
            <p className="mt-3 text-[11px] leading-4 text-gray-500">Catalogue matches are advisory and do not guarantee official eligibility or benefits.</p>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Shortcut icon={<UserRound className="h-4 w-4" />} title="Business Profile" text="Update reusable business data" target="/dashboard/profile" />
        <Shortcut icon={<FileWarning className="h-4 w-4" />} title="Documents" text="Review project documents" target={`/dashboard/${projectId}/documents`} />
        <Shortcut icon={<Sparkles className="h-4 w-4" />} title="Regulatory Copilot" text="Ask about requirements" target={`/dashboard/${projectId}/copilot`} />
        <Shortcut icon={<LifeBuoy className="h-4 w-4" />} title="Grievances" text="Track operational issues" target="/dashboard/grievances" />
      </section>

      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs leading-5 text-slate-600">
        <span className="font-semibold text-slate-800">Prototype transparency:</span> this command center composes existing UDYOGSETU records. Government statuses/integrations are not live in this prototype; SLA/risk values are advisory; scheme matches use the configured catalogue.
        <span className="ml-1">Generated {formatDate(data.metadata.generated_at, true)}.</span>
      </div>
    </div>
  )
}

function MetricBar({ label, value, trailing }: { label: string; value: number; trailing: string }) {
  return (
    <div>
      <div className="flex items-center justify-between gap-3 text-xs">
        <span className="font-medium text-gray-700">{label}</span>
        <span className="text-gray-500">{trailing}</span>
      </div>
      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-gray-100">
        <div className="h-full rounded-full bg-blue-600" style={{ width: `${Math.max(0, Math.min(100, value || 0))}%` }} />
      </div>
    </div>
  )
}

function MetricTile({ label, value, emphasis = false }: { label: string; value: string; emphasis?: boolean }) {
  return (
    <div className={`rounded-lg border p-3 ${emphasis ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-gray-50'}`}>
      <p className="text-[10px] font-medium uppercase tracking-wide text-gray-500">{label}</p>
      <p className={`mt-1 font-bold ${emphasis ? 'text-green-800' : 'text-gray-900'}`}>{value}</p>
    </div>
  )
}

function Stat({ label, value, danger = false }: { label: string; value: number; danger?: boolean }) {
  return (
    <div className="rounded-lg bg-gray-50 p-2">
      <p className="font-semibold text-gray-900">{value}</p>
      <p className={`mt-0.5 ${danger ? 'text-red-600' : 'text-gray-500'}`}>{label}</p>
    </div>
  )
}

function EmptyState({ icon, text }: { icon: ReactNode; text: string }) {
  return <div className="rounded-xl border border-dashed border-gray-200 p-6 text-center text-sm text-gray-500"><div className="mx-auto w-fit text-gray-400">{icon}</div><p className="mt-2">{text}</p></div>
}

function Shortcut({ icon, title, text, target }: { icon: ReactNode; title: string; text: string; target: string }) {
  const router = useRouter()
  return (
    <button type="button" onClick={() => router.push(target)} className="rounded-xl border border-gray-200 bg-white p-4 text-left transition hover:-translate-y-0.5 hover:border-gray-300 hover:shadow-sm">
      <div className="flex items-center gap-2 text-blue-700"><span className="rounded-lg bg-blue-50 p-2">{icon}</span><span className="font-semibold text-gray-900">{title}</span></div>
      <p className="mt-2 text-xs text-gray-500">{text}</p>
    </button>
  )
}

export default UnifiedCommandCenter
