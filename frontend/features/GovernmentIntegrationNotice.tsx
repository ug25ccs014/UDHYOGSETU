'use client'

import { ExternalLink, Info, ShieldCheck, TestTube2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

type Integration = {
  classification?: string
  label?: string
  status?: string
  source_label?: string
  provider?: string
  is_simulated?: boolean
  gateway_system?: string | null
  external_portal_url?: string | null
  submission_handling?: string
  note?: string
}

export default function GovernmentIntegrationNotice({ integration }: { integration?: Integration }) {
  if (!integration) return null

  const simulated = Boolean(integration.is_simulated)
  const external = integration.classification === 'EXTERNAL_PORTAL'
  const future = integration.classification === 'FUTURE_AUTHORIZED_API'
  const authorized = integration.classification === 'AUTHORIZED_API'

  return (
    <Card className={simulated ? 'border-amber-200 bg-amber-50/60' : future ? 'border-slate-200 bg-slate-50' : 'border-blue-200 bg-blue-50/60'}>
      <CardHeader className="pb-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            {simulated ? <TestTube2 className="h-5 w-5 text-amber-700" /> : authorized ? <ShieldCheck className="h-5 w-5 text-teal-700" /> : <Info className="h-5 w-5 text-blue-700" />}
            Integration handling
          </CardTitle>
          <Badge variant={simulated ? 'warning' : authorized ? 'success' : 'outline'}>
            {integration.label || 'Integration'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-slate-700">
        <div className="grid gap-2 sm:grid-cols-3">
          <div><span className="text-slate-500">Source</span><div className="font-medium text-slate-900">{integration.source_label || 'Not specified'}</div></div>
          <div><span className="text-slate-500">System</span><div className="font-medium text-slate-900">{integration.gateway_system || '—'}</div></div>
          <div><span className="text-slate-500">Status</span><div className="font-medium text-slate-900">{integration.status || '—'}</div></div>
        </div>

        <div className="rounded-xl border border-white/80 bg-white/70 p-3 leading-6">
          {integration.note}
        </div>

        {external && integration.external_portal_url && (
          <a
            href={integration.external_portal_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 font-medium text-blue-700 hover:underline"
          >
            Open official portal <ExternalLink className="h-4 w-4" />
          </a>
        )}

        {future && (
          <p className="text-xs text-slate-600">
            This service is deliberately not treated as an integrated government API until an authorized adapter is configured.
          </p>
        )}
      </CardContent>
    </Card>
  )
}
