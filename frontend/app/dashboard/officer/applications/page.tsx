'use client'

import { useState } from 'react'
import Link from 'next/link'
import { ClipboardList, Loader2, ArrowRight, RefreshCw } from 'lucide-react'
import { useOfficerApplications } from '@/hooks/useApi'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

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

const filters = ['ALL', 'NOT_STARTED', 'DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'INSPECTION', 'QUERY_RAISED', 'APPROVED', 'REJECTED']

export default function OfficerApplicationsPage() {
  const [status, setStatus] = useState('')
  const [q, setQ] = useState('')
  const { data, isLoading, isError, refetch } = useOfficerApplications({
    status: status || undefined,
    q: q || undefined,
  })

  const applications: any[] = data?.applications || []

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Application Review</h1>
          <p className="mt-1 text-gray-600">
            Review and act on applications submitted by entrepreneurs
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} className="w-full sm:w-auto">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="flex flex-wrap gap-2 items-center">
        {filters.map((f) => (
          <Button
            key={f}
            variant={status === f || (f === 'ALL' && status === '') ? 'default' : 'outline'}
            size="sm"
            onClick={() => setStatus(f === 'ALL' ? '' : f)}
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
            <p className="text-lg text-gray-900">Unable to load applications</p>
            <p className="mt-2 text-gray-600">Officer or Admin access required.</p>
          </CardContent>
        </Card>
      ) : applications.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <ClipboardList className="w-10 h-10 mx-auto text-gray-300" />
            <p className="mt-4 text-gray-600">No applications match the current filters.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Application</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Entrepreneur</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Company</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Status</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Risk</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {applications.map((app: any) => (
                  <tr key={app.approval_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="font-medium text-gray-900 capitalize">{app.approval_name}</div>
                      <div className="text-xs text-gray-500">{app.department}</div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {app.owner_name || '—'}
                      <div className="text-xs text-gray-500">{app.owner_email}</div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">{app.company_name}</td>
                    <td className="px-6 py-4">
                      <Badge variant={statusVariant(app.status)}>{app.status.replace('_', ' ')}</Badge>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">{app.risk_level}</td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        href={`/dashboard/officer/applications/${app.approval_id}`}
                        className="inline-flex items-center gap-1 text-sm font-medium text-blue-600"
                      >
                        Review
                        <ArrowRight className="w-4 h-4" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}