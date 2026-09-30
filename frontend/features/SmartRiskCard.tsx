'use client'

import { AlertTriangle, CheckCircle2, Clock3, ShieldAlert } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useSlaRiskApplication } from '@/hooks/useApi'

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

export default function SmartRiskCard({ applicationId }: { applicationId: string }) {
  const { data, isLoading, isError } = useSlaRiskApplication(applicationId)

  if (isLoading) {
    return <Card><CardContent className="p-6 text-sm text-gray-500">Loading risk signals…</CardContent></Card>
  }

  if (isError || !data) {
    return null
  }

  return (
    <Card className="border-slate-200">
      <CardHeader className="pb-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldAlert className="h-5 w-5 text-blue-600" />
            Smart SLA Risk
          </CardTitle>
          <div className="flex flex-wrap gap-2">
            <Badge variant={riskVariant(data.risk_band)}>{data.risk_band} risk</Badge>
            <Badge variant={slaVariant(data.sla.status)}>{data.sla.status.replace(/_/g, ' ')}</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-xl bg-gray-50 p-3">
            <p className="text-xs text-gray-500">Risk score</p>
            <p className="mt-1 text-xl font-bold text-gray-900">{data.risk_score}/100</p>
          </div>
          <div className="rounded-xl bg-gray-50 p-3">
            <p className="text-xs text-gray-500">Days remaining</p>
            <p className="mt-1 text-xl font-bold text-gray-900">{data.sla.days_remaining}</p>
          </div>
          <div className="rounded-xl bg-gray-50 p-3">
            <p className="text-xs text-gray-500">Open queries</p>
            <p className="mt-1 text-xl font-bold text-gray-900">{data.signals.query_open_count}</p>
          </div>
          <div className="rounded-xl bg-gray-50 p-3">
            <p className="text-xs text-gray-500">Doc issues</p>
            <p className="mt-1 text-xl font-bold text-gray-900">{data.signals.document_issue_count}</p>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-gray-100 p-4">
            <div className="flex items-center gap-2">
              {data.sla.status === 'BREACHED' ? <AlertTriangle className="h-4 w-4 text-red-600" /> : <Clock3 className="h-4 w-4 text-gray-500" />}
              <p className="text-sm font-semibold text-gray-900">SLA signal</p>
            </div>
            <p className="mt-2 text-sm text-gray-600">{data.sla.reason}</p>
            {data.sla.deadline && <p className="mt-2 text-xs text-gray-500">Configured deadline: {data.sla.deadline}</p>}
          </div>

          <div className="rounded-xl border border-gray-100 p-4">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-teal-600" />
              <p className="text-sm font-semibold text-gray-900">Operational signals</p>
            </div>
            <ul className="mt-2 space-y-1 text-sm text-gray-600">
              <li>Queries: {data.signals.query_open_count ? `${data.signals.query_open_count} open` : 'none open'}</li>
              <li>Inspection: {data.signals.inspection_scheduled ? 'scheduled' : 'none scheduled'}</li>
              <li>Documents: {data.signals.document_issue_count ? `${data.signals.document_issue_count} issue(s)` : 'no flagged issues'}</li>
            </ul>
          </div>
        </div>

        {data.recommended_actions?.length > 0 && (
          <div className="rounded-xl bg-blue-50 p-4">
            <p className="text-sm font-semibold text-blue-950">Suggested next actions</p>
            <ul className="mt-2 space-y-1 text-sm text-blue-900">
              {data.recommended_actions.slice(0, 3).map((action: string) => (
                <li key={action}>• {action}</li>
              ))}
            </ul>
          </div>
        )}

        <p className="text-xs text-gray-500">Predictive assistance only. This signal does not replace statutory review or determine an application's outcome.</p>
      </CardContent>
    </Card>
  )
}
