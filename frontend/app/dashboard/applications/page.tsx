'use client'

import { useState } from 'react'
import Link from 'next/link'
import { ClipboardList, Loader2, ArrowRight, Plus, Clock, CheckCircle2 } from 'lucide-react'
import { useApplications } from '@/hooks/useApi'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import OfflineDraftsPanel from '@/features/OfflineDraftsPanel'
import PageHeader, { StatCard } from '@/components/PageHeader'
import { useLanguage } from '@/lib/language'

function statusVariant(status: string): 'success' | 'danger' | 'default' | 'warning' | 'info' | 'outline' {
  switch (status) {
    case 'APPROVED':
      return 'success'
    case 'REJECTED':
      return 'danger'
    case 'QUERY_RAISED':
      return 'warning'
    case 'INSPECTION':
      return 'info'
    case 'SUBMITTED':
    case 'UNDER_REVIEW':
      return 'default'
    default:
      return 'outline'
  }
}

const filters = [
  'ALL',
  'NOT_STARTED',
  'DRAFT',
  'SUBMITTED',
  'UNDER_REVIEW',
  'QUERY_RAISED',
  'APPROVED',
]

export default function ApplicationsPage() {
  const { t, statusLabel } = useLanguage()
  const { data, isLoading, isError, refetch, isFetching } = useApplications()
  const [filter, setFilter] = useState('ALL')

  const applications: any[] = data?.applications || []
  const filtered =
    filter === 'ALL' ? applications : applications.filter((a) => a.status === filter)

  const active = applications.filter((a) => a.status === 'SUBMITTED' || a.status === 'UNDER_REVIEW').length
  const approved = applications.filter((a) => a.status === 'APPROVED').length

  return (
    <div className="space-y-6">
      <PageHeader
        icon={ClipboardList}
        title={t('pg.appsTitle')}
        purpose={t('pg.appsPurpose')}
        action={<Link href="/dashboard/explore"><Button><Plus className="h-4 w-4" /> {t('pg.newApp')}</Button></Link>}
      />

      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        <StatCard icon={ClipboardList} label={t('pg.totalApps')} value={applications.length} />
        <StatCard icon={Clock} tone="bg-sun/30 text-navy-ink" label={t('pg.inProgress')} value={active} hint={t('pg.inProgressHint')} />
        <StatCard icon={CheckCircle2} tone="bg-teal-100 text-teal-700" label={t('pg.approved')} value={approved} />
      </div>

      <OfflineDraftsPanel />

      {data?.__offlineCachedAt && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Showing your latest locally cached application list. Government status updates require an online connection.
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {filters.map((f) => {
          const count = f === 'ALL' ? applications.length : applications.filter((a) => a.status === f).length
          return (
            <Button
              key={f}
              variant={filter === f ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilter(f)}
            >
              {f === 'ALL' ? t('pg.all') : statusLabel(f)}
              <span className={`rounded-full px-1.5 text-xs ${filter === f ? 'bg-white/20' : 'bg-gray-100 text-gray-600'}`}>{count}</span>
            </Button>
          )
        })}
      </div>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-24 text-gray-600">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          <p className="mt-4 text-sm">Loading applications...</p>
        </div>
      ) : isError ? (
        <Card>
          <CardContent className="py-16 text-center">
            <ClipboardList className="w-10 h-10 mx-auto text-gray-300" aria-hidden="true" />
            <p className="mt-4 font-medium text-gray-900">We couldn’t load your applications.</p>
            <p className="mt-1 text-sm text-gray-600">Check your connection and try again.</p>
            <Button className="mt-4" variant="outline" onClick={() => refetch()} disabled={isFetching}>
              {isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Retry
            </Button>
          </CardContent>
        </Card>
      ) : applications.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <ClipboardList className="w-10 h-10 mx-auto text-gray-300" aria-hidden="true" />
            <p className="mt-4 font-medium text-gray-900">No applications yet</p>
            <p className="mt-1 text-sm text-gray-600">Start from the service catalogue to create your first application.</p>
            <Link
              href="/dashboard/explore"
              className="mt-5 inline-flex items-center gap-1 rounded-full bg-navy px-5 py-2 text-sm font-semibold text-cream transition hover:bg-navy-2"
            >
              Explore government services →
            </Link>
          </CardContent>
        </Card>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-gray-600">No applications for this filter.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white/90 shadow-card">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-gray-200 bg-gray-100/70">
                <tr>
                  <th className="px-6 py-3.5 text-left text-xs font-extrabold uppercase tracking-wider text-gray-500">Application</th>
                  <th className="px-6 py-3.5 text-left text-xs font-extrabold uppercase tracking-wider text-gray-500">Department</th>
                  <th className="px-6 py-3.5 text-left text-xs font-extrabold uppercase tracking-wider text-gray-500">Status</th>
                  <th className="px-6 py-3.5 text-left text-xs font-extrabold uppercase tracking-wider text-gray-500">Processed (days)</th>
                  <th className="px-6 py-3.5 text-left text-xs font-extrabold uppercase tracking-wider text-gray-500"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filtered.map((app: any) => {
                  const isDraft = app.status === 'NOT_STARTED' || app.status === 'DRAFT'
                  return (
                    <tr key={app.application_id} className="transition hover:bg-blue-50/60">
                      <td className="px-6 py-4">
                        <div className="font-medium text-gray-900 capitalize">{app.approval_name}</div>
                        <div className="text-xs text-gray-500">{app.project_name}</div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">{app.department}</td>
                      <td className="px-6 py-4">
                        <Badge variant={statusVariant(app.status)}>
                          {statusLabel(app.status)}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {app.estimated_processing_days
                          ? `${app.estimated_processing_days} days`
                          : '—'}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <Link
                          href={app.status === 'QUERY_RAISED' ? `/dashboard/applications/${app.application_id}/query` : `/dashboard/applications/${app.application_id}`}
                          className="inline-flex items-center gap-1 rounded-full bg-navy px-3.5 py-1.5 text-sm font-semibold text-cream transition hover:bg-navy-2"
                        >
                          {app.status === 'QUERY_RAISED' ? 'Resolve query' : isDraft ? 'Continue' : 'Track'}
                          <ArrowRight className="w-4 h-4" />
                        </Link>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}