'use client'

import { useParams, useRouter } from 'next/navigation'
import { useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, FileText, Loader2, RefreshCw } from 'lucide-react'
import {
  useOfficerApplication,
  useOfficerTransition,
  useOfficerSync,
} from '@/hooks/useApi'
import { Button } from '@/components/ui/button'
import Breadcrumbs from '@/components/Breadcrumbs'
import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
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

export default function OfficerApplicationDetailPage() {
  const params = useParams()
  const router = useRouter()
  const queryClient = useQueryClient()
  const applicationId = params.applicationId as string

  const { data: app, isLoading } = useOfficerApplication(applicationId)
  const transition = useOfficerTransition()
  const sync = useOfficerSync()
  const [actionError, setActionError] = useState('')

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['officer-application'] })
    queryClient.invalidateQueries({ queryKey: ['officer-applications'] })
    queryClient.invalidateQueries({ queryKey: ['applications'] })
  }

  const runTransition = async (to: string) => {
    setActionError('')
    try {
      await transition.mutateAsync({ applicationId, toStatus: to })
      invalidate()
    } catch (e: any) {
      console.error(e)
      setActionError(e?.response?.data?.detail || 'The application status could not be updated. Please try again.')
    }
  }

  const runSync = async () => {
    setActionError('')
    try {
      await sync.mutateAsync(applicationId)
      invalidate()
    } catch (e: any) {
      console.error(e)
      setActionError(e?.response?.data?.detail || 'The government status could not be synchronized. Please try again.')
    }
  }

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-gray-600">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        <p className="mt-4 text-sm">Loading application...</p>
      </div>
    )
  }

  if (!app) {
    return (
      <Card>
        <CardContent className="py-16 text-center">
          <p className="text-lg text-gray-900">Application not found</p>
        </CardContent>
      </Card>
    )
  }

  const available = app.available_transitions || []

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Officer Applications', href: '/dashboard/officer/applications' }, { label: app.approval_name }]} />
      <Button variant="ghost" size="sm" onClick={() => router.push('/dashboard/officer/applications')}>
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Review Queue
      </Button>

      {actionError && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{actionError}</div>}

      <div className="flex items-start justify-between flex-wrap gap-4">
        <div className="flex items-center gap-2">
          <h1 className="text-3xl font-bold text-gray-900 capitalize">{app.approval_name}</h1>
          <Badge variant={statusVariant(app.status)}>{app.status.replace('_', ' ')}</Badge>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={runSync} disabled={sync.isPending}>
            <RefreshCw className="w-4 h-4 mr-2" />
            {sync.isPending ? 'Syncing...' : 'Sync status'}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-3">
          <h3 className="font-semibold text-gray-900">Entrepreneur</h3>
          <p className="font-medium text-gray-900">{app.owner_name}</p>
          <p className="text-sm text-gray-600">{app.owner_email}</p>
          <p className="text-sm text-gray-600">{app.company_name}</p>
          <div className="border-t border-gray-100 pt-3 text-sm text-gray-500">
            <div>Department: {app.department}</div>
            <div>Risk: {app.risk_level}</div>
            <div>Mandatory: {app.is_mandatory ? 'Yes' : 'No'}</div>
            <div>Source: {app.source || 'roadmap'}</div>
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6 col-span-2">
          <h3 className="font-semibold text-gray-900 mb-3">Government Sync</h3>
          {app.government && (app.government.system || app.government.government_application_id) ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">System</span>
                <span className="font-medium text-gray-900">{app.government.system}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Government Application ID</span>
                <span className="font-medium text-gray-900">{app.government.government_application_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Last synced status</span>
                <Badge variant="outline">{app.government.last_synced_status || '—'}</Badge>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-500">
              This application has not been tracked against a government system yet.
            </p>
          )}

          <h3 className="font-semibold text-gray-900 mt-6 mb-3">Linked Documents</h3>
          {app.documents && app.documents.length > 0 ? (
            <ul className="space-y-2">
              {app.documents.map((doc: any) => (
                <li key={doc.id} className="flex items-center gap-3 text-sm">
                  <FileText className="w-4 h-4 text-gray-400" />
                  <span className="font-medium text-gray-900">{doc.file_name}</span>
                  <Badge variant="outline">{(doc.document_type || 'untagged').toUpperCase()}</Badge>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500">No documents linked to this project yet.</p>
          )}

          {available.length > 0 && (
            <>
              <h3 className="font-semibold text-gray-900 mt-6 mb-3">Officer Actions</h3>
              <div className="flex flex-wrap gap-2">
                {available.map((t: any) => (
                  <Button
                    key={t.to}
                    size="sm"
                    variant={t.to === 'APPROVED' ? 'default' : t.to === 'REJECTED' ? 'danger' : 'outline'}
                    onClick={() => runTransition(t.to)}
                    disabled={transition.isPending}
                    title={t.side_effect}
                  >
                    {t.label}
                  </Button>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}