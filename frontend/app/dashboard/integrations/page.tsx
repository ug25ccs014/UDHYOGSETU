'use client'

import { useLanguage } from '@/lib/language'
import PageHeader from '@/components/PageHeader'
import { ExternalLink, Info, Loader2, RefreshCw, ShieldCheck, TestTube2 } from 'lucide-react'
import { useState } from 'react'
import { useGatewayCatalog, useGatewayHealth } from '@/hooks/useApi'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

function badgeVariant(classification: string): 'success' | 'warning' | 'info' | 'outline' {
  if (classification === 'AUTHORIZED_API') return 'success'
  if (classification === 'PROTOTYPE_SIMULATOR') return 'warning'
  if (classification === 'EXTERNAL_PORTAL') return 'info'
  return 'outline'
}

function friendlyStatus(item: any) {
  if (item.classification === 'PROTOTYPE_SIMULATOR') return 'Prototype Available'
  if (item.classification === 'AUTHORIZED_API') return 'Connected'
  if (item.classification === 'FUTURE_AUTHORIZED_API') return 'Not Configured'
  return item.status || '—'
}

export default function IntegrationsPage() {
  const { t } = useLanguage()
  const [showHealth, setShowHealth] = useState(false)
  const { data, isLoading, isError } = useGatewayCatalog()
  const health = useGatewayHealth(showHealth)

  const systems = data?.systems || []
  const summary = data?.summary
  const healthBySystem = health.data?.systems || {}

  return (
    <div className="space-y-8">
      <PageHeader
        icon={ShieldCheck}
        title={t('pg.integTitle')}
        purpose={t('pg.integPurpose')}
        action={
          <Button variant="outline" onClick={() => setShowHealth((value) => !value)}>
            <RefreshCw className="h-4 w-4" />
            {showHealth ? t('pg.hideChecks') : t('pg.runChecks')}
          </Button>
        }
      />

      {data?.disclaimer && (
        <Card className="border-blue-200 bg-blue-50/70">
          <CardContent className="p-5 text-sm leading-6 text-blue-900">
            <div className="flex gap-3"><Info className="mt-0.5 h-5 w-5 shrink-0" /><span>{data.disclaimer}</span></div>
          </CardContent>
        </Card>
      )}

      {summary && (
        <div className="grid grid-cols-2 gap-5 lg:grid-cols-6">
          <Card><CardContent className="p-5"><p className="text-xs font-extrabold uppercase tracking-wider text-gray-500">Systems</p><p className="mt-1 text-3xl font-extrabold tracking-tight">{summary.total_systems}</p></CardContent></Card>
          <Card><CardContent className="p-5"><p className="text-xs font-extrabold uppercase tracking-wider text-gray-500">Configured</p><p className="mt-1 text-3xl font-extrabold tracking-tight">{summary.configured_systems}</p></CardContent></Card>
          <Card><CardContent className="p-5"><p className="text-xs font-extrabold uppercase tracking-wider text-gray-500">Prototype</p><p className="mt-1 text-3xl font-extrabold tracking-tight text-navy-ink">{summary.simulated_systems}</p></CardContent></Card>
          <Card><CardContent className="p-5"><p className="text-xs font-extrabold uppercase tracking-wider text-gray-500">Authorized</p><p className="mt-1 text-3xl font-extrabold tracking-tight text-teal-700">{summary.authorized_systems}</p></CardContent></Card>
          <Card><CardContent className="p-5"><p className="text-xs font-extrabold uppercase tracking-wider text-gray-500">Future API</p><p className="mt-1 text-3xl font-extrabold tracking-tight text-gray-600">{summary.future_authorized_systems}</p></CardContent></Card>
          <Card><CardContent className="p-5"><p className="text-xs font-extrabold uppercase tracking-wider text-gray-500">External Portal</p><p className="mt-1 text-3xl font-extrabold tracking-tight text-blue-700">{summary.external_portal_systems}</p></CardContent></Card>
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-20 text-gray-600"><Loader2 className="mr-2 h-5 w-5 animate-spin" />Loading integration catalog...</div>
      ) : isError ? (
        <Card><CardContent className="py-16 text-center text-gray-600">Integration catalog unavailable.</CardContent></Card>
      ) : (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {systems.map((item: any) => {
            const runtime = healthBySystem[item.system]
            return (
              <Card key={item.system} className="h-full">
                <CardHeader>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${item.is_simulated ? 'bg-amber-100' : 'bg-blue-50'}`}>
                        {item.is_simulated ? <TestTube2 className="h-5 w-5 text-amber-700" /> : <ShieldCheck className="h-5 w-5 text-blue-700" />}
                      </div>
                      <div><CardTitle className="text-base">{item.display_name}</CardTitle><p className="text-xs text-gray-500">{item.system}</p></div>
                    </div>
                    <Badge variant={badgeVariant(item.classification)}>{item.label || friendlyStatus(item)}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4 text-sm">
                  <div className="grid grid-cols-2 gap-3">
                    <div><p className="text-gray-500">Provider</p><p className="font-medium">{item.provider}</p></div>
                    <div><p className="text-gray-500">Status</p><p className="font-medium">{friendlyStatus(item)}</p></div>
                  </div>
                  <div className="rounded-xl bg-gray-50 p-3 leading-6 text-gray-600">{item.note}</div>
                  <div className="flex flex-wrap gap-2 text-xs text-gray-600">
                    {item.supports_services && <Badge variant="outline">Service discovery</Badge>}
                    {item.supports_status && <Badge variant="outline">Status</Badge>}
                    {item.supports_submission && <Badge variant="outline">Submission</Badge>}
                  </div>
                  {runtime && (
                    <div className="rounded-xl border border-gray-200 p-3">
                      <div className="flex items-center justify-between"><span className="text-gray-500">Prototype runtime</span><Badge variant={runtime.runtime_status === 'HEALTHY' ? 'success' : 'outline'}>{runtime.runtime_status}</Badge></div>
                      <p className="mt-2 text-xs text-gray-500">Availability signal: {runtime.availability_pct}% · Probes: {runtime.probes}</p>
                    </div>
                  )}
                  {item.official_portal_url && (
                    <a href={item.official_portal_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm font-medium text-blue-700 hover:underline">Official portal <ExternalLink className="h-4 w-4" /></a>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      <Card className="border-slate-200">
        <CardContent className="p-5 text-sm leading-6 text-slate-600">
          <strong className="text-slate-900">Architecture seam:</strong> authorized adapters can be injected behind the same gateway interface later. Until then, no prototype status is treated as an official government response.
        </CardContent>
      </Card>
    </div>
  )
}
