'use client'

import { useState } from 'react'
import Link from 'next/link'
import { ClipboardList, Loader2, ArrowRight } from 'lucide-react'
import { useApplications } from '@/hooks/useApi'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import OfflineDraftsPanel from '@/features/OfflineDraftsPanel'

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
  const { data, isLoading, isError, refetch, isFetching } = useApplications()
  const [filter, setFilter] = useState('ALL')

  const applications: any[] = data?.applications || []
  const filtered =
    filter === 'ALL' ? applications : applications.filter((a) => a.status === filter)

  const active = applications.filter((a) => a.status === 'SUBMITTED' || a.status === 'UNDER_REVIEW').length
  const approved = applications.filter((a) => a.status === 'APPROVED').length

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Applications</h1>
        <p className="mt-1 text-gray-600">
          Track every government application you have started or submitted
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <div className="text-sm text-gray-600">Total Applications</div>
          <div className="text-3xl font-bold mt-1 text-blue-600">{applications.length}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <div className="text-sm text-gray-600">In Progress</div>
          <div className="text-3xl font-bold mt-1 text-yellow-600">{active}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <div className="text-sm text-gray-600">Approved</div>
          <div className="text-3xl font-bold mt-1 text-green-600">{approved}</div>
        </div>
      </div>

      <OfflineDraftsPanel />

      {data?.__offlineCachedAt && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Showing your latest locally cached application list. Government status updates require an online connection.
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {filters.map((f) => (
          <Button
            key={f}
            variant={filter === f ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter(f)}
          >
            {f.replace('_', ' ')}
          </Button>
        ))}
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
              className="inline-flex mt-4 text-sm font-medium text-blue-600 underline"
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
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Application</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Department</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Status</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Processed (days)</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filtered.map((app: any) => {
                  const isDraft = app.status === 'NOT_STARTED' || app.status === 'DRAFT'
                  return (
                    <tr key={app.application_id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <div className="font-medium text-gray-900 capitalize">{app.approval_name}</div>
                        <div className="text-xs text-gray-500">{app.project_name}</div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">{app.department}</td>
                      <td className="px-6 py-4">
                        <Badge variant={statusVariant(app.status)}>
                          {app.status.replace('_', ' ')}
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
                          className="inline-flex items-center gap-1 text-sm font-medium text-blue-600"
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