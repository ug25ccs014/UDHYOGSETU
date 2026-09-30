'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import {
  ArrowUpRight,
  BadgeCheck,
  Check,
  ExternalLink,
  FileCheck2,
  FileText,
  Gift,
  Loader2,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  UploadCloud,
} from 'lucide-react'
import { useParams } from 'next/navigation'
import {
  usePrepareIncentiveApplication,
  useProject,
  useProjectIncentiveReadiness,
  useUpdateIncentiveCase,
} from '@/hooks/useApi'
import type { IncentiveReadiness } from '@/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'

function readinessVariant(state: string): 'success' | 'warning' | 'danger' | 'info' | 'outline' {
  if (state === 'READY') return 'success'
  if (state === 'REVIEW_RECOMMENDED') return 'info'
  if (state === 'ACTION_REQUIRED') return 'warning'
  if (state === 'NOT_MATCHED') return 'danger'
  return 'outline'
}

function criterionVariant(status: string): 'success' | 'warning' | 'danger' | 'outline' {
  if (status === 'MET') return 'success'
  if (status === 'REVIEW') return 'warning'
  if (status === 'NOT_MET') return 'danger'
  return 'outline'
}

function formatCurrency(value?: number | null) {
  if (value == null) return '—'
  return `₹${Number(value).toLocaleString('en-IN')}`
}

function SchemeCard({ projectId, scheme }: { projectId: string; scheme: IncentiveReadiness }) {
  const prepare = usePrepareIncentiveApplication()
  const updateCase = useUpdateIncentiveCase()
  const [open, setOpen] = useState(false)
  const [selectedDocs, setSelectedDocs] = useState<string[]>([])
  const [notes, setNotes] = useState('')
  const [externalReference, setExternalReference] = useState('')
  const [localError, setLocalError] = useState('')
  const [preparedCase, setPreparedCase] = useState<{ case_id: string; status: string } | null>(null)

  const readyDocs = useMemo(
    () => scheme.required_documents.filter((doc) => doc.status === 'READY' && doc.document_id),
    [scheme.required_documents],
  )

  const selected = selectedDocs.length ? selectedDocs : readyDocs.map((doc) => doc.document_id!).filter(Boolean)
  const isPreparing = prepare.isPending || updateCase.isPending
  const caseId = preparedCase?.case_id || scheme.case?.case_id
  const caseStatus = preparedCase?.status || scheme.case?.status
  const canRecordSubmission = Boolean(caseId) && caseStatus === 'READY_FOR_SUBMISSION'

  const toggleDoc = (documentId: string) => {
    setSelectedDocs((current) => {
      const effective = current.length ? current : selected
      return effective.includes(documentId)
        ? effective.filter((id) => id !== documentId)
        : [...effective, documentId]
    })
  }

  const prepareApplication = async () => {
    setLocalError('')
    try {
      const result = await prepare.mutateAsync({
        projectId,
        schemeId: scheme.scheme_id,
        documentIds: selected,
        notes: notes || undefined,
      })
      setPreparedCase({ case_id: result.case_id, status: result.status })
      setOpen(true)
    } catch (error: any) {
      setLocalError(error?.response?.data?.detail || 'Could not prepare the incentive application pack.')
    }
  }

  const recordSubmission = async () => {
    if (!caseId) return
    setLocalError('')
    try {
      await updateCase.mutateAsync({
        caseId,
        payload: {
          status: 'SUBMITTED_EXTERNALLY',
          external_reference: externalReference || undefined,
        },
      }).then((result) => setPreparedCase({ case_id: result.case_id, status: result.status }))
    } catch (error: any) {
      setLocalError(error?.response?.data?.detail || 'Could not record the external submission.')
    }
  }

  const documentReady = scheme.document_summary.ready
  const documentRequired = scheme.document_summary.required

  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-4">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <Gift className="w-5 h-5 text-blue-600" />
              <CardTitle className="text-lg">{scheme.name}</CardTitle>
              <Badge variant={readinessVariant(scheme.readiness_state)}>
                {scheme.readiness_state.replace('_', ' ')}
              </Badge>
            </div>
            <CardDescription className="mt-1">
              {scheme.department}{scheme.sector ? ` · ${scheme.sector}` : ''}
            </CardDescription>
          </div>
          <div className="text-left lg:text-right">
            <p className="text-xs uppercase tracking-wide text-gray-500">Catalogue match</p>
            <p className="text-2xl font-bold text-gray-900">{Math.round(scheme.match_score)}%</p>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Readiness</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">{scheme.readiness_score}%</p>
            <p className="mt-1 text-xs text-gray-600">Preparation completeness</p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Documents</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">{documentReady}/{documentRequired}</p>
            <p className="mt-1 text-xs text-gray-600">Required documents ready</p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Application period</p>
            <p className="mt-1 text-sm font-semibold text-gray-900 line-clamp-2">{scheme.application_period || 'Not configured'}</p>
            <p className="mt-1 text-xs text-gray-600">Confirm current official window</p>
          </div>
        </div>

        <div className="rounded-lg border border-blue-100 bg-blue-50 p-4">
          <div className="flex items-start gap-3">
            <Sparkles className="w-5 h-5 text-blue-600 mt-0.5" />
            <div>
              <p className="font-semibold text-blue-900">Why this scheme appears</p>
              <p className="mt-1 text-sm text-blue-800">{scheme.match_reason || 'Matched by the configured catalogue rules.'}</p>
            </div>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between gap-3 mb-3">
            <h3 className="font-semibold text-gray-900">Eligibility checks</h3>
            {scheme.eligibility.manual_confirmation_required && (
              <Badge variant="warning">Official confirmation required</Badge>
            )}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {scheme.eligibility.criteria.map((criterion) => (
              <div key={criterion.key} className="rounded-lg border border-gray-200 p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-gray-900">{criterion.label}</p>
                  <Badge variant={criterionVariant(criterion.status)}>{criterion.status.replace('_', ' ')}</Badge>
                </div>
                <p className="mt-2 text-xs leading-5 text-gray-600">{criterion.detail}</p>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between gap-3 mb-3">
            <h3 className="font-semibold text-gray-900">Application documents</h3>
            <Link href={`/dashboard/profile`} className="text-sm text-blue-600 hover:underline">
              Open Data Vault
            </Link>
          </div>
          {scheme.required_documents.length === 0 ? (
            <div className="rounded-lg border border-dashed border-gray-300 p-5 text-sm text-gray-600">
              No required documents are configured for this catalogue entry.
            </div>
          ) : (
            <div className="space-y-2">
              {scheme.required_documents.map((doc) => {
                const effectiveSelected = selected.includes(doc.document_id || '')
                return (
                  <div key={`${scheme.scheme_id}-${doc.requirement}`} className="rounded-lg border border-gray-200 p-4">
                    <div className="flex items-start gap-3">
                      <div className="pt-0.5">
                        {doc.status === 'READY' && doc.document_id ? (
                          <button
                            type="button"
                            onClick={() => toggleDoc(doc.document_id!)}
                            aria-label={`${effectiveSelected ? 'Remove' : 'Select'} ${doc.file_name || doc.requirement}`}
                            className={`w-5 h-5 rounded border flex items-center justify-center ${effectiveSelected ? 'bg-blue-600 border-blue-600 text-white' : 'border-gray-300 bg-white'}`}
                          >
                            {effectiveSelected && <Check className="w-3.5 h-3.5" />}
                          </button>
                        ) : doc.status === 'MISSING' ? (
                          <UploadCloud className="w-5 h-5 text-yellow-600" />
                        ) : (
                          <ShieldAlert className="w-5 h-5 text-red-600" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-3 flex-wrap">
                          <p className="text-sm font-medium text-gray-900">{doc.requirement}</p>
                          <Badge variant={doc.status === 'READY' ? 'success' : doc.status === 'MISSING' ? 'warning' : 'danger'}>
                            {doc.status.replace('_', ' ')}
                          </Badge>
                        </div>
                        {doc.file_name ? (
                          <p className="mt-1 text-xs text-gray-600">
                            {doc.file_name} · {doc.project_name || 'Current project'}{doc.in_vault ? ' · Data Vault' : ''}
                          </p>
                        ) : (
                          <p className="mt-1 text-xs text-gray-600">No matching document found in your reusable documents.</p>
                        )}
                        {doc.validation_errors?.length ? (
                          <p className="mt-1 text-xs text-red-600">{doc.validation_errors[0]}</p>
                        ) : null}
                        {doc.status === 'MISSING' && doc.candidates?.length ? (
                          <p className="mt-2 text-xs text-blue-700">Possible matches are available in your project/document vault.</p>
                        ) : null}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {scheme.benefits?.length > 0 && (
          <div>
            <h3 className="font-semibold text-gray-900 mb-2">Configured benefits</h3>
            <div className="space-y-2">
              {scheme.benefits.map((benefit) => (
                <div key={benefit} className="flex items-start gap-2 text-sm text-gray-700">
                  <BadgeCheck className="w-4 h-4 text-green-600 mt-0.5 shrink-0" />
                  {benefit}
                </div>
              ))}
            </div>
          </div>
        )}

        {open || scheme.case?.case_id ? (
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="font-semibold text-gray-900">Application preparation</p>
                <p className="text-sm text-gray-600 mt-1">
                  {caseId ? `Case ${caseId}` : 'Preparation pack is being created.'}
                </p>
              </div>
              {caseStatus && <Badge variant={caseStatus === 'READY_FOR_SUBMISSION' ? 'success' : 'info'}>{caseStatus.replace(/_/g, ' ')}</Badge>}
            </div>

            {canRecordSubmission && (
              <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-3 items-end">
                <div>
                  <label className="text-sm font-medium text-gray-700">Official/external reference (optional)</label>
                  <input
                    value={externalReference}
                    onChange={(event) => setExternalReference(event.target.value)}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    placeholder="e.g. acknowledgement number"
                  />
                </div>
                <Button onClick={recordSubmission} disabled={isPreparing} variant="outline">
                  {updateCase.isPending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <ExternalLink className="w-4 h-4 mr-2" />}
                  Record External Submission
                </Button>
              </div>
            )}

            <p className="text-xs text-gray-500">
              This records applicant preparation/submission activity only. UDYOGSETU does not transmit an application to a government system in this prototype.
            </p>
          </div>
        ) : null}

        {localError && <p className="text-sm text-red-600">{localError}</p>}

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-2 border-t border-gray-200">
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <FileCheck2 className="w-4 h-4" />
            <span>{selected.length} reusable document(s) selected</span>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href={`/dashboard/${projectId}/documents`}>
              <Button variant="outline" size="sm">
                <FileText className="w-4 h-4 mr-2" />
                Manage Documents
              </Button>
            </Link>
            <Button
              onClick={prepareApplication}
              disabled={isPreparing || scheme.readiness_state === 'NOT_MATCHED'}
              size="sm"
            >
              {prepare.isPending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <FileCheck2 className="w-4 h-4 mr-2" />}
              {caseId ? 'Refresh Preparation Pack' : 'Prepare Application Pack'}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function IncentiveReadinessCenter() {
  const params = useParams()
  const projectId = params.projectId as string
  const { data: project, isLoading: projectLoading } = useProject(projectId)
  const { data, isLoading, isError, refetch } = useProjectIncentiveReadiness(projectId)

  if (projectLoading || isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-gray-600">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        <p className="mt-4 text-sm">Building incentive readiness...</p>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <Card>
        <CardContent className="py-16 text-center">
          <Gift className="w-10 h-10 mx-auto text-gray-300" />
          <p className="mt-4 text-gray-900 font-medium">Unable to load incentive readiness</p>
          <p className="mt-1 text-sm text-gray-600">The scheme catalogue or project data could not be evaluated.</p>
          <Button className="mt-5" variant="outline" onClick={() => refetch()}>
            <RefreshCw className="w-4 h-4 mr-2" /> Retry
          </Button>
        </CardContent>
      </Card>
    )
  }

  const matches: IncentiveReadiness[] = data.matches || []

  return (
    <div className="space-y-6">
      <div>
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-3xl font-bold text-gray-900">Incentive Application Readiness</h1>
              <Badge variant="info">Advisory</Badge>
            </div>
            <p className="mt-2 text-gray-600">
              Prepare scheme applications using your project profile and reusable documents without repeatedly entering the same information.
            </p>
            <p className="mt-2 text-xs text-gray-500">
              Project: {project?.name || data.project_name}
            </p>
          </div>
          <Link href={`/dashboard/${projectId}`}>
            <Button variant="outline" size="sm">
              <ArrowUpRight className="w-4 h-4 mr-2" />
              Command Center
            </Button>
          </Link>
        </div>
      </div>

      <div className="rounded-xl border border-blue-100 bg-blue-50 p-5">
        <div className="flex items-start gap-3">
          <Gift className="w-6 h-6 text-blue-600 mt-0.5" />
          <div>
            <p className="font-semibold text-blue-900">How this works</p>
            <p className="mt-1 text-sm text-blue-800">
              UDYOGSETU uses the configured incentive catalogue to identify matches, then checks your profile and reusable documents for application readiness. Final eligibility, benefits and current application windows must be confirmed against the official scheme notice.
            </p>
          </div>
        </div>
      </div>

      {matches.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <Gift className="w-10 h-10 mx-auto text-gray-300" />
            <p className="mt-4 text-gray-900 font-medium">No configured scheme matches found</p>
            <p className="mt-1 text-sm text-gray-600">Review your project profile or the active scheme catalogue.</p>
          </CardContent>
        </Card>
      ) : (
        matches.map((scheme) => (
          <SchemeCard key={scheme.scheme_id} projectId={projectId} scheme={scheme} />
        ))
      )}
    </div>
  )
}
