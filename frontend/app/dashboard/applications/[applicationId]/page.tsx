'use client'

import { useParams, useRouter } from 'next/navigation'
import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { AlertCircle, ArrowLeft, FileText, Loader2, MessageSquareWarning, ShieldCheck, Sparkles } from 'lucide-react'
import {
  useApplication,
  useApplicationTransitions,
  useSlaStatus,
  useApplicationReadiness,
  useTransitionApplication,
} from '@/hooks/useApi'
import PreSubmissionReadiness from '@/features/PreSubmissionReadiness'
import SmartRiskCard from '@/features/SmartRiskCard'
import InspectionApplicationPanel from '@/features/InspectionApplicationPanel'
import { Button } from '@/components/ui/button'
import Breadcrumbs from '@/components/Breadcrumbs'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { useOfflineStatus } from '@/hooks/useOfflineStatus'

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

function slaVariant(status: string): 'success' | 'warning' | 'danger' | 'default' | 'info' | 'outline' {
  switch (status) {
    case 'ON_TRACK':
      return 'success'
    case 'AT_RISK':
      return 'warning'
    case 'BREACHED':
      return 'danger'
    case 'COMPLETED':
      return 'info'
    default:
      return 'outline'
  }
}

export default function ApplicationDetailPage() {
  const params = useParams()
  const router = useRouter()
  const queryClient = useQueryClient()
  const applicationId = params.applicationId as string

  const { data: application, isLoading } = useApplication(applicationId)
  const { data: transitions } = useApplicationTransitions(applicationId)
  const { data: sla } = useSlaStatus(applicationId)
  const { data: readiness } = useApplicationReadiness(applicationId)
  const { isOnline } = useOfflineStatus()
  const transition = useTransitionApplication()
  const [transitionError, setTransitionError] = useState('')

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-gray-600">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        <p className="mt-4 text-sm">Loading application...</p>
      </div>
    )
  }

  if (!application) {
    return (
      <Card>
        <CardContent className="py-16 text-center">
          <p className="text-lg font-medium text-gray-900">Application not found</p>
          <p className="mt-1 text-sm text-gray-600">The application may have been removed or you may not have access to it.</p>
          <Button className="mt-4" variant="outline" onClick={() => router.push('/dashboard/applications')}>Back to Applications</Button>
        </CardContent>
      </Card>
    )
  }

  const available = transitions?.available_transitions || []

  const runTransition = async (to: string) => {
    setTransitionError('')
    if (!isOnline) {
      setTransitionError('You are offline. Actions that change server or government state are unavailable until the connection is restored.')
      return
    }
    try {
      await transition.mutateAsync({ applicationId, toStatus: to })
      queryClient.invalidateQueries({ queryKey: ['application'] })
      queryClient.invalidateQueries({ queryKey: ['application-transitions'] })
      queryClient.invalidateQueries({ queryKey: ['application-sla'] })
      queryClient.invalidateQueries({ queryKey: ['applications'] })
    } catch (e: any) {
      console.error(e)
      setTransitionError(e?.response?.data?.detail || 'The application status could not be updated. Please try again.')
    }
  }

  const status = application.status

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Applications', href: '/dashboard/applications' }, { label: application.approval_name }]} />
      <Button variant="ghost" size="sm" onClick={() => router.push('/dashboard/applications')}>
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Applications
      </Button>

      {application.__offlineCachedAt && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Showing the latest locally cached application snapshot. Actions that change government or server state remain blocked until you are online.
        </div>
      )}

      {transitionError && (
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{transitionError}</div>
      )}

      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold text-gray-900 capitalize">{application.approval_name}</h1>
            <Badge variant={statusVariant(status)}>{status.replace('_', ' ')}</Badge>
          </div>
          <p className="mt-1 text-gray-600">{application.department}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {(status === 'NOT_STARTED' || status === 'DRAFT') && (
            <Button size="sm" variant="default" onClick={() => router.push(`/dashboard/applications/${applicationId}/prepare`)}>
              <Sparkles className="mr-2 h-4 w-4" />
              Prepare application
            </Button>
          )}
          {available.length > 0 && (
            <div className="space-y-1 text-right">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Available actions</p>
            <div className="flex flex-wrap gap-2">
              {available.map((t: any) => (
                <Button
                  key={t.to}
                  size="sm"
                  variant={t.to === 'SUBMITTED' ? 'default' : 'outline'}
                  onClick={() => runTransition(t.to)}
                  disabled={
                    transition.isPending ||
                    (t.to === 'SUBMITTED' && (!isOnline || (readiness?.submission_eligible && readiness?.can_submit !== true)))
                  }
                  title={
                    t.to === 'SUBMITTED' && !isOnline
                      ? 'Submission requires an online connection'
                      : t.to === 'SUBMITTED' && readiness?.submission_eligible && readiness?.can_submit !== true
                        ? 'Resolve pre-submission readiness checks first'
                        : undefined
                  }
                >
                  {t.label}
                </Button>
              ))}
            </div>
          </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border border-gray-200 rounded-lg p-6 col-span-1">
          <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-blue-600" />
            SLA Status
          </h3>
          {sla ? (
            <div className="space-y-2">
              <Badge variant={slaVariant(sla.status)}>{sla.status.replace('_', ' ')}</Badge>
              <p className="text-sm text-gray-700">{sla.reason}</p>
              <div className="grid grid-cols-2 gap-2 text-sm pt-2">
                <div className="text-gray-500">Elapsed</div>
                <div className="text-right font-medium text-gray-900">{sla.days_elapsed} days</div>
                <div className="text-gray-500">Remaining</div>
                <div className="text-right font-medium text-gray-900">{sla.days_remaining} days</div>
                <div className="text-gray-500">Deadline</div>
                <div className="text-right font-medium text-gray-900">{sla.deadline || '—'}</div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-500">SLA not yet computed.</p>
          )}
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6 col-span-2">
          <h3 className="font-semibold text-gray-900 mb-3">Details</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <div className="text-gray-500">Application ID</div>
            <div className="font-medium text-gray-900">{application.application_id}</div>
            <div className="text-gray-500">Project</div>
            <div className="font-medium text-gray-900">{application.project_name || '—'}</div>
            <div className="text-gray-500">Processing Time</div>
            <div className="font-medium text-gray-900">
              {application.estimated_processing_days
                ? `${application.estimated_processing_days} days`
                : '—'}
            </div>
            <div className="text-gray-500">Submitted At</div>
            <div className="font-medium text-gray-900">
              {application.submitted_at
                ? new Date(application.submitted_at).toLocaleString()
                : 'Not submitted'}
            </div>
            <div className="text-gray-500">Approved At</div>
            <div className="font-medium text-gray-900">
              {application.approved_at ? new Date(application.approved_at).toLocaleString() : '—'}
            </div>
          </div>
        </div>
      </div>

      <SmartRiskCard applicationId={applicationId} />

      <Card className="border-slate-200">
        <CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <MessageSquareWarning className="mt-0.5 h-5 w-5 shrink-0 text-blue-700" />
            <div>
              <p className="font-semibold text-slate-950">Need to report an application issue?</p>
              <p className="mt-1 text-sm text-slate-600">Create a grievance and follow its status through an auditable escalation workflow.</p>
            </div>
          </div>
          <Button variant="outline" onClick={() => router.push(`/dashboard/grievances?applicationId=${encodeURIComponent(applicationId)}`)}>
            Raise grievance
          </Button>
        </CardContent>
      </Card>

      {status === 'QUERY_RAISED' && (
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" />
              <div>
                <p className="font-semibold text-amber-950">Department query requires your attention</p>
                <p className="mt-1 text-sm text-amber-900">Open the Query & Response Center to understand the request, attach evidence and prepare your response.</p>
              </div>
            </div>
            <Button onClick={() => router.push(`/dashboard/applications/${applicationId}/query`)}>
              Resolve query
            </Button>
          </CardContent>
        </Card>
      )}

      <PreSubmissionReadiness
        applicationId={applicationId}
        applicationStatus={application.status}
      />

      <InspectionApplicationPanel applicationId={applicationId} />

      <Card>
        <CardContent className="p-6">
          <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-600" />
            Journey
          </h3>
          <div className="text-sm text-gray-600">
            This application was started from the{' '}
            <span className="font-medium">Explore Government Services</span> journey and flows
            through the same tracking, SLA and officer review pipeline as every other approval.
            Upload documents from the service page to attach them here.
          </div>
        </CardContent>
      </Card>
    </div>
  )
}