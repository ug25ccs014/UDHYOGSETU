'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Bell,
  BriefcaseBusiness,
  CheckCircle2,
  ClipboardList,
  Clock3,
  FileWarning,
  Gauge,
  Loader2,
  RefreshCw,
  Search,
  ShieldAlert,
  Users,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useOfficerCommandCenter } from '@/hooks/useApi'
import { getSessionUser } from '@/lib/auth'

type OfficerDashboardProps = {
  user?: any
}

function statusVariant(status: string) {
  switch (status) {
    case 'APPROVED':
      return 'success' as const
    case 'REJECTED':
      return 'danger' as const
    case 'QUERY_RAISED':
      return 'warning' as const
    case 'INSPECTION':
      return 'info' as const
    default:
      return 'outline' as const
  }
}

function riskVariant(risk: string) {
  switch (risk) {
    case 'HIGH':
      return 'danger' as const
    case 'MEDIUM':
      return 'warning' as const
    case 'LOW':
      return 'success' as const
    default:
      return 'outline' as const
  }
}

function formatDate(value?: string | null) {
  if (!value) return '—'
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? '—' : parsed.toLocaleString()
}

function progressPercent(application: any) {
  const slaDays = Number(application?.sla?.sla_days || 0)
  const elapsed = Number(application?.sla?.days_elapsed || 0)
  if (!slaDays) return 0
  return Math.min(100, Math.max(0, (elapsed / slaDays) * 100))
}

export function OfficerDashboard({ user }: OfficerDashboardProps) {
  const [sessionUser, setSessionUser] = useState<any>(user || null)
  const [department, setDepartment] = useState('')
  const [risk, setRisk] = useState('')
  const [search, setSearch] = useState('')

  useEffect(() => {
    if (!user) setSessionUser(getSessionUser())
  }, [user])

  const isOfficer = sessionUser?.role === 'OFFICER' || sessionUser?.role === 'ADMIN'
  const params = useMemo(
    () => ({
      department: department || undefined,
      risk: risk || undefined,
      limit: 25,
    }),
    [department, risk],
  )
  const { data, isLoading, isError, refetch, isFetching } = useOfficerCommandCenter(params, isOfficer)

  const overview = data?.overview ?? {}
  const queue = useMemo(() => {
    const items = Array.isArray(data?.priority_queue) ? data.priority_queue : []
    const needle = search.trim().toLowerCase()
    if (!needle) return items
    return items.filter((item: any) =>
      [item.application_id, item.approval_name, item.company_name, item.project_name, item.department]
        .map((value) => String(value || '').toLowerCase())
        .some((value) => value.includes(needle)),
    )
  }, [data?.priority_queue, search])

  const departmentChart = (data?.departments || []).slice(0, 8).map((item: any) => ({
    department: item.department.length > 18 ? `${item.department.slice(0, 18)}…` : item.department,
    pending: item.pending || 0,
    breaches: item.sla_breaches || 0,
  }))

  const statusTotal = (data?.distribution || []).reduce((sum: number, item: any) => sum + Number(item.count || 0), 0)

  if (!isOfficer) {
    return (
      <Card className="max-w-2xl mx-auto">
        <CardContent className="py-16 text-center">
          <ShieldAlert className="w-10 h-10 mx-auto text-red-500" />
          <h1 className="mt-4 text-xl font-semibold text-gray-900">Officer access required</h1>
          <p className="mt-2 text-gray-600">This command center is available only to authorized officers and administrators.</p>
        </CardContent>
      </Card>
    )
  }

  if (isLoading && !data) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-gray-600">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        <p className="mt-4 text-sm">Loading officer command center...</p>
      </div>
    )
  }

  if (isError && !data) {
    return (
      <Card>
        <CardContent className="py-16 text-center">
          <AlertTriangle className="w-10 h-10 mx-auto text-red-500" />
          <h1 className="mt-4 text-xl font-semibold text-gray-900">Unable to load officer analytics</h1>
          <p className="mt-2 text-gray-600">The live officer command center could not be loaded.</p>
          <Button className="mt-6" onClick={() => refetch()}>Try again</Button>
        </CardContent>
      </Card>
    )
  }

  const kpis = [
    { label: 'Total Applications', value: overview.total_applications ?? 0, icon: BriefcaseBusiness, href: '/dashboard/officer/applications' },
    { label: 'Active Review Queue', value: overview.review_queue_count ?? 0, icon: ClipboardList, href: '/dashboard/officer/applications' },
    { label: 'SLA Breaches', value: overview.sla_breached ?? overview.sla_breaches ?? 0, icon: Clock3, href: '/dashboard/sla-risk' },
    { label: 'High Risk', value: overview.high_risk ?? 0, icon: ShieldAlert, href: '/dashboard/sla-risk' },
    { label: 'Open Queries', value: overview.open_queries ?? 0, icon: FileWarning, href: '/dashboard/officer/applications' },
    { label: 'Open Grievances', value: overview.open_grievances ?? 0, icon: Bell, href: '/dashboard/grievances' },
  ]

  return (
    <div className="space-y-6 sm:space-y-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-3xl font-bold text-gray-900">Officer Command Center</h1>
            <Badge variant="outline">Live operational data</Badge>
          </div>
          <p className="mt-2 text-gray-600">
            Triage applications, monitor SLA pressure, and identify workflow bottlenecks from one screen.
          </p>
          <p className="mt-1 text-sm text-gray-500">
            {sessionUser?.name || 'Officer'} · {sessionUser?.role === 'ADMIN' ? 'Administrator' : 'Authorized Officer'}
          </p>
        </div>
        <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className={`w-4 h-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh snapshot
        </Button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        {kpis.map((kpi) => {
          const Icon = kpi.icon
          return (
            <Link key={kpi.label} href={kpi.href} className="block">
              <Card className="h-full hover:shadow-md transition-shadow">
                <CardContent className="p-4 sm:p-5">
                  <div className="flex items-start justify-between gap-2">
                    <Icon className="w-5 h-5 text-blue-600" />
                    <ArrowRight className="w-4 h-4 text-gray-300" />
                  </div>
                  <p className="mt-4 text-sm text-gray-600">{kpi.label}</p>
                  <p className="mt-1 text-2xl font-bold text-gray-900">{kpi.value}</p>
                </CardContent>
              </Card>
            </Link>
          )
        })}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Card className="xl:col-span-2">
          <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Priority review queue</CardTitle>
              <p className="mt-1 text-sm text-gray-500">Sorted by SLA pressure, operational risk, and urgency.</p>
            </div>
            <Link href="/dashboard/officer/applications" className="text-sm font-medium text-blue-600 hover:underline">
              Open full queue →
            </Link>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-5">
              <div className="md:col-span-2 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search applicant, company, application..." className="pl-9" />
              </div>
              <div className="flex gap-2">
                <select value={risk} onChange={(event) => setRisk(event.target.value)} className="min-w-0 flex-1 h-10 rounded-md border border-gray-300 bg-white px-3 text-sm">
                  <option value="">All risk</option>
                  <option value="HIGH">High</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="LOW">Low</option>
                </select>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 mb-5">
              <Button size="sm" variant={!department ? 'default' : 'outline'} onClick={() => setDepartment('')}>All departments</Button>
              {(data?.departments || []).slice(0, 6).map((item: any) => (
                <Button key={item.department} size="sm" variant={department === item.department ? 'default' : 'outline'} onClick={() => setDepartment(item.department)}>
                  {item.department}
                </Button>
              ))}
            </div>

            {queue.length === 0 ? (
              <div className="py-12 text-center text-gray-600">
                <CheckCircle2 className="w-10 h-10 mx-auto text-green-500" />
                <p className="mt-3 font-medium text-gray-900">No matching priority cases</p>
                <p className="mt-1 text-sm">Adjust the filters or open the complete review queue.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {queue.map((app: any) => (
                  <div key={app.approval_id} className="rounded-xl border border-gray-200 p-4 hover:border-blue-200 transition-colors">
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <Link href={`/dashboard/officer/applications/${encodeURIComponent(app.application_id)}`} className="font-semibold text-gray-900 hover:text-blue-600">
                            {app.approval_name}
                          </Link>
                          <Badge variant={riskVariant(app.risk_band)}>{app.risk_band}</Badge>
                          <Badge variant={statusVariant(app.status)}>{String(app.status).replaceAll('_', ' ')}</Badge>
                        </div>
                        <p className="mt-1 text-sm text-gray-600">{app.company_name || '—'} · {app.department}</p>
                        <p className="text-xs text-gray-500 mt-1">{app.project_name || 'Project'}{app.project_location ? ` · ${app.project_location}` : ''}</p>
                      </div>
                      <div className="text-left lg:text-right shrink-0">
                        <p className="text-sm font-semibold text-gray-900">Risk score {app.risk_score}</p>
                        <p className="text-xs text-gray-500 mt-1">{app.sla.days_remaining >= 0 ? `${app.sla.days_remaining} days remaining` : `${Math.abs(app.sla.days_remaining)} days overdue`}</p>
                      </div>
                    </div>

                    <div className="mt-4">
                      <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                        <span>SLA: {app.sla.status.replaceAll('_', ' ')}</span>
                        <span>{app.sla.days_elapsed} / {app.sla.sla_days} days</span>
                      </div>
                      <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
                        <div className="h-full bg-blue-600 rounded-full" style={{ width: `${progressPercent(app)}%` }} />
                      </div>
                    </div>

                    <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="rounded-lg bg-gray-50 p-3">
                        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Key signals</p>
                        <ul className="mt-2 space-y-1 text-sm text-gray-700">
                          {(app.key_risk_factors || []).slice(0, 3).map((factor: string) => <li key={factor}>• {factor}</li>)}
                        </ul>
                      </div>
                      <div className="rounded-lg bg-gray-50 p-3">
                        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Recommended action</p>
                        <p className="mt-2 text-sm text-gray-700">{app.recommended_actions?.[0] || 'Review application details.'}</p>
                      </div>
                    </div>

                    <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-gray-500">
                      <span>Updated SLA deadline: {formatDate(app.sla.deadline)}</span>
                      <Link href={`/dashboard/officer/applications/${encodeURIComponent(app.application_id)}`} className="inline-flex items-center gap-1 text-sm font-medium text-blue-600">
                        Review case <ArrowRight className="w-4 h-4" />
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Workload health</CardTitle>
              <p className="text-sm text-gray-500">Current operational pressure.</p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between"><span className="text-sm text-gray-600">SLA on track</span><Badge variant="success">{overview.total_applications ? Math.round(((overview.sla_on_track || 0) / overview.total_applications) * 100) : 0}%</Badge></div>
              <div className="flex items-center justify-between"><span className="text-sm text-gray-600">High risk</span><Badge variant="danger">{overview.high_risk ?? 0}</Badge></div>
              <div className="flex items-center justify-between"><span className="text-sm text-gray-600">Medium risk</span><Badge variant="warning">{overview.medium_risk ?? 0}</Badge></div>
              <div className="flex items-center justify-between"><span className="text-sm text-gray-600">Awaiting applicant</span><Badge variant="outline">{overview.awaiting_applicant ?? 0}</Badge></div>
              <div className="pt-2 border-t border-gray-100 grid grid-cols-2 gap-3">
                <Link href="/dashboard/inspections" className="rounded-lg border border-gray-200 p-3 hover:bg-gray-50">
                  <Gauge className="w-5 h-5 text-blue-600" />
                  <p className="mt-2 text-xs text-gray-500">Inspections</p>
                  <p className="font-semibold text-gray-900">{overview.scheduled_inspections ?? 0}</p>
                </Link>
                <Link href="/dashboard/grievances" className="rounded-lg border border-gray-200 p-3 hover:bg-gray-50">
                  <AlertTriangle className="w-5 h-5 text-orange-500" />
                  <p className="mt-2 text-xs text-gray-500">Grievances</p>
                  <p className="font-semibold text-gray-900">{overview.open_grievances ?? 0}</p>
                </Link>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Throughput</CardTitle>
              <p className="text-sm text-gray-500">Submitted applications recorded by UDYOGSETU.</p>
            </CardHeader>
            <CardContent className="grid grid-cols-3 gap-3">
              <div><p className="text-xs text-gray-500">Today</p><p className="text-2xl font-bold text-gray-900">{data?.throughput?.submissions_today ?? 0}</p></div>
              <div><p className="text-xs text-gray-500">7 days</p><p className="text-2xl font-bold text-gray-900">{data?.throughput?.submissions_7d ?? 0}</p></div>
              <div><p className="text-xs text-gray-500">30 days</p><p className="text-2xl font-bold text-gray-900">{data?.throughput?.submissions_30d ?? 0}</p></div>
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-3">
            <div>
              <CardTitle>Department performance</CardTitle>
              <p className="mt-1 text-sm text-gray-500">Pending workload and SLA breaches by department.</p>
            </div>
            <BarChart3 className="w-5 h-5 text-gray-400" />
          </CardHeader>
          <CardContent>
            {departmentChart.length === 0 ? (
              <p className="py-12 text-center text-gray-500">No department data yet.</p>
            ) : (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={departmentChart} margin={{ top: 8, right: 12, bottom: 8, left: -8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="department" tick={{ fontSize: 11 }} interval={0} angle={-20} textAnchor="end" height={55} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="pending" name="Pending" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="breaches" name="SLA Breaches" fill="#ef4444" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Operational bottlenecks</CardTitle>
            <p className="mt-1 text-sm text-gray-500">Workflow stages and signals currently holding work.</p>
          </CardHeader>
          <CardContent>
            {data?.bottlenecks?.length ? (
              <div className="space-y-4">
                {data.bottlenecks.map((item: any) => (
                  <div key={item.name}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <p className="font-medium text-gray-900">{item.name}</p>
                        <p className="mt-1 text-xs text-gray-500">{item.description}</p>
                      </div>
                      <div className="text-right shrink-0">
                        <p className="text-lg font-bold text-gray-900">{item.count}</p>
                        <p className="text-xs text-gray-500">{item.share_percent}%</p>
                      </div>
                    </div>
                    <div className="mt-2 h-2 rounded-full bg-gray-100 overflow-hidden">
                      <div className="h-full bg-amber-500 rounded-full" style={{ width: `${Math.min(100, item.share_percent)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-12 text-center text-gray-500">
                <CheckCircle2 className="w-9 h-9 mx-auto text-green-500" />
                <p className="mt-3 font-medium text-gray-900">No active bottleneck signal</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>Application status distribution</CardTitle>
            <p className="mt-1 text-sm text-gray-500">{statusTotal} applications represented in the current snapshot.</p>
          </div>
          <Users className="w-5 h-5 text-gray-400" />
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-6 gap-3">
            {(data?.distribution || []).map((item: any) => (
              <div key={item.status} className="rounded-lg border border-gray-200 p-3">
                <Badge variant={statusVariant(item.status)}>{String(item.status).replaceAll('_', ' ')}</Badge>
                <p className="mt-2 text-2xl font-bold text-gray-900">{item.count}</p>
                <p className="text-xs text-gray-500">{statusTotal ? Math.round((item.count / statusTotal) * 100) : 0}% of total</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="rounded-lg border border-blue-100 bg-blue-50 p-4 text-sm text-blue-900">
        <strong>Operational note:</strong> This dashboard uses UDYOGSETU's configured workflow, SLA and risk data. Risk indicators are predictive assistance for triage, not statutory determinations, official government ratings, or guarantees of processing time.
      </div>
    </div>
  )
}

export default OfficerDashboard
