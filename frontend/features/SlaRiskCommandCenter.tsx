'use client'

import PageHeader from '@/components/PageHeader'
import Link from 'next/link'
import {
  ArrowRight,
  CheckCircle2,
  Clock3,
  Gauge,
  ShieldAlert,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { SlaRiskApplication, SlaRiskPortfolio } from '@/types'

function riskVariant(risk: string): 'danger' | 'warning' | 'success' | 'outline' {
  if (risk === 'HIGH') return 'danger'
  if (risk === 'MEDIUM') return 'warning'
  if (risk === 'LOW') return 'success'
  return 'outline'
}

function slaVariant(status: string): 'danger' | 'warning' | 'success' | 'info' | 'outline' {
  if (status === 'BREACHED') return 'danger'
  if (status === 'AT_RISK') return 'warning'
  if (status === 'ON_TRACK') return 'success'
  if (status === 'COMPLETED') return 'info'
  return 'outline'
}

function ApplicationCard({ application, audience }: { application: SlaRiskApplication; audience: 'ENTREPRENEUR' | 'OFFICER' }) {
  const appId = application.application_id
  const reviewHref = audience === 'OFFICER'
    ? `/dashboard/officer/applications/${encodeURIComponent(appId)}`
    : `/dashboard/applications/${encodeURIComponent(appId)}`
  return (
    <Card className="overflow-hidden">
      <CardContent className="p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="truncate font-semibold text-gray-900">{application.approval_name}</p>
            <p className="mt-1 text-sm text-gray-500">
              {application.department} · {application.status.replace(/_/g, ' ')}
            </p>
            {(application.project_name || application.company_name || application.project_location) && (
              <p className="mt-1 text-xs text-gray-500">
                {[application.project_name, application.company_name, application.project_location].filter(Boolean).join(' · ')}
              </p>
            )}
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <Badge variant={riskVariant(application.risk_band)}>{application.risk_band} risk</Badge>
            <Badge variant={slaVariant(application.sla.status)}>{application.sla.status.replace(/_/g, ' ')}</Badge>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-xl bg-gray-50 p-3">
            <p className="text-xs text-gray-500">Risk score</p>
            <p className="mt-1 text-lg font-semibold text-gray-900">{application.risk_score}/100</p>
          </div>
          <div className="rounded-xl bg-gray-50 p-3">
            <p className="text-xs text-gray-500">Remaining</p>
            <p className="mt-1 text-lg font-semibold text-gray-900">
              {application.sla.days_remaining}d
            </p>
          </div>
          <div className="rounded-xl bg-gray-50 p-3">
            <p className="text-xs text-gray-500">Query</p>
            <p className="mt-1 text-lg font-semibold text-gray-900">
              {application.signals.query_open_count || '—'}
            </p>
          </div>
          <div className="rounded-xl bg-gray-50 p-3">
            <p className="text-xs text-gray-500">Documents</p>
            <p className="mt-1 text-lg font-semibold text-gray-900">
              {application.signals.document_issue_count || '—'}
            </p>
          </div>
        </div>

        <div className="mt-4 flex flex-col gap-3 rounded-xl border border-gray-100 bg-white">
          <div className="flex items-center justify-between px-4 pt-3">
            <span className="text-sm font-medium text-gray-700">Why this needs attention</span>
            <span className="text-xs text-gray-500">
              {Math.round(application.breach_probability * 100)}% estimated breach probability
            </span>
          </div>
          <ul className="space-y-1 px-4 pb-3 text-sm text-gray-600">
            {application.key_risk_factors.slice(0, 3).map((factor) => (
              <li key={factor} className="flex gap-2">
                <span className="mt-1 text-gray-400">•</span>
                <span>{factor}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-xs text-gray-500">
            Predictive assistance only · not a statutory determination.
          </div>
          <Link href={reviewHref}>
            <Button variant="outline" size="sm">
              Review application
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  )
}

interface Props {
  data?: SlaRiskPortfolio
  loading?: boolean
  error?: boolean
  title?: string
  subtitle?: string
  audience?: 'ENTREPRENEUR' | 'OFFICER'
}

export default function SlaRiskCommandCenter({ data, loading, error, title = 'SLA & Smart Risk', subtitle = 'See where attention is needed before service timelines are missed.', audience = 'ENTREPRENEUR' }: Props) {
  const [filter, setFilter] = useState<'ALL' | 'HIGH' | 'MEDIUM' | 'BREACHED' | 'AT_RISK'>('ALL')
  const filteredApplications = useMemo(() => {
    const applications = data?.applications ?? []
    if (filter === 'ALL') return applications
    if (filter === 'BREACHED') return applications.filter((item) => item.sla.status === 'BREACHED')
    if (filter === 'AT_RISK') return applications.filter((item) => item.sla.status === 'AT_RISK')
    return applications.filter((item) => item.risk_band === filter)
  }, [data?.applications, filter])

  if (loading) {
    return <div className="py-16 text-center text-sm text-gray-500">Loading SLA and risk signals…</div>
  }

  if (error || !data) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="font-medium text-gray-900">SLA risk data unavailable</p>
          <p className="mt-1 text-sm text-gray-500">Refresh the page and try again.</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader icon={Gauge} title={title} purpose={subtitle} />

      <Card className="border-blue-100 bg-blue-50/60">
        <CardContent className="flex flex-col gap-2 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-blue-700" />
            <div>
              <p className="font-semibold text-blue-950">Decision-support signal</p>
              <p className="mt-1 text-sm text-blue-900">
                Risk is estimated from configured SLA rules plus persisted application signals such as queries, inspections and document issues. It does not make or replace a statutory decision.
              </p>
            </div>
          </div>
          <Badge variant="outline" className="w-fit border-blue-200 bg-white">Predictive assistance</Badge>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card><CardHeader className="p-5 pb-2"><CardTitle className="text-sm text-gray-500">Applications</CardTitle></CardHeader><CardContent className="p-5 pt-1"><p className="text-3xl font-extrabold tracking-tight text-gray-900">{data.total_applications}</p><p className="mt-1 text-xs text-gray-500">in this view</p></CardContent></Card>
        <Card><CardHeader className="p-5 pb-2"><CardTitle className="text-sm text-gray-500">High risk</CardTitle></CardHeader><CardContent className="p-5 pt-1"><p className="text-3xl font-extrabold tracking-tight text-red-600">{data.high_risk}</p><p className="mt-1 text-xs text-gray-500">needs priority review</p></CardContent></Card>
        <Card><CardHeader className="p-5 pb-2"><CardTitle className="text-sm text-gray-500">SLA at risk</CardTitle></CardHeader><CardContent className="p-5 pt-1"><p className="text-3xl font-extrabold tracking-tight text-yellow-600">{data.sla_at_risk}</p><p className="mt-1 text-xs text-gray-500">75%+ of window used</p></CardContent></Card>
        <Card><CardHeader className="p-5 pb-2"><CardTitle className="text-sm text-gray-500">Breached</CardTitle></CardHeader><CardContent className="p-5 pt-1"><p className="text-3xl font-extrabold tracking-tight text-red-600">{data.sla_breached}</p><p className="mt-1 text-xs text-gray-500">past configured SLA</p></CardContent></Card>
      </div>

      {data.applications.length === 0 ? (
        <Card>
          <CardContent className="py-14 text-center">
            <CheckCircle2 className="mx-auto h-10 w-10 text-teal-600" />
            <p className="mt-4 font-medium text-gray-900">No active SLA risk items</p>
            <p className="mt-1 text-sm text-gray-500">Applications will appear here when they have a live SLA or operational risk signal.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2">
              <Clock3 className="h-5 w-5 text-gray-500" />
              <h2 className="text-lg font-semibold text-gray-900">Priority queue</h2>
            </div>
            <div className="flex flex-wrap gap-2">
              {[
                ['ALL', 'All'],
                ['HIGH', 'High risk'],
                ['MEDIUM', 'Medium'],
                ['BREACHED', 'SLA breached'],
                ['AT_RISK', 'SLA at risk'],
              ].map(([value, label]) => (
                <Button
                  key={value}
                  size="sm"
                  variant={filter === value ? 'default' : 'outline'}
                  onClick={() => setFilter(value as typeof filter)}
                >
                  {label}
                </Button>
              ))}
            </div>
          </div>
          {filteredApplications.length === 0 ? (
            <Card><CardContent className="py-10 text-center text-sm text-gray-500">No applications match this filter.</CardContent></Card>
          ) : filteredApplications.map((application) => (
            <ApplicationCard key={application.approval_id} application={application} audience={audience} />
          ))}
        </div>
      )}
    </div>
  )
}
