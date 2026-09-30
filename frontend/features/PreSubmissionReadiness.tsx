'use client'

import { useState } from 'react'
import Link from 'next/link'
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  FileCheck2,
  FileWarning,
  Loader2,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import {
  useApplicationReadiness,
  useAttachApplicationDocument,
  useValidateDocument,
} from '@/hooks/useApi'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface PreSubmissionReadinessProps {
  applicationId: string
  applicationStatus?: string
}

function checkVariant(status: string): 'success' | 'warning' | 'danger' | 'outline' {
  if (status === 'PASS') return 'success'
  if (status === 'WARNING') return 'warning'
  if (status === 'BLOCKED') return 'danger'
  return 'outline'
}

function issueIcon(severity: string) {
  return severity === 'BLOCKER' ? CircleAlert : AlertCircle
}

export function PreSubmissionReadiness({ applicationId, applicationStatus }: PreSubmissionReadinessProps) {
  const queryClient = useQueryClient()
  const { data, isLoading, isError, refetch, isFetching } = useApplicationReadiness(applicationId)
  const validateDocument = useValidateDocument()
  const attachApplicationDocument = useAttachApplicationDocument()
  const [expanded, setExpanded] = useState(false)
  const [error, setError] = useState('')

  const handleValidate = async (documentId: string) => {
    setError('')
    try {
      await validateDocument.mutateAsync(documentId)
      await queryClient.invalidateQueries({ queryKey: ['application-readiness', applicationId] })
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Document validation could not be completed.')
    }
  }

  const handleAttach = async (documentId: string) => {
    setError('')
    try {
      await attachApplicationDocument.mutateAsync({ applicationId, documentId })
      await queryClient.invalidateQueries({ queryKey: ['application-readiness', applicationId] })
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Document could not be attached to this application.')
    }
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-3 py-8 text-gray-600">
          <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
          Checking pre-submission readiness...
        </CardContent>
      </Card>
    )
  }

  if (isError || !data) {
    return (
      <Card>
        <CardContent className="py-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-semibold text-gray-900">Readiness check unavailable</p>
              <p className="mt-1 text-sm text-gray-600">
                We could not evaluate this application right now. No submission decision was inferred.
              </p>
            </div>
            <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
              <RefreshCw className={`mr-2 h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  const blockingIssues = data.blocking_issues || []
  const warnings = data.warnings || []
  const actions = data.next_actions || []
  const checklist = data.document_checklist || []
  const isPreSubmission = data.submission_eligible ?? ['NOT_STARTED', 'DRAFT'].includes(applicationStatus || data.application_status)

  return (
    <Card className="overflow-hidden">
      <CardHeader className="border-b border-gray-100 bg-gradient-to-r from-white to-blue-50/40">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-blue-600" />
              <CardTitle>Pre-Submission Readiness</CardTitle>
              <Badge variant={checkVariant(data.readiness_state === 'READY' ? 'PASS' : data.readiness_state === 'BLOCKED' ? 'BLOCKED' : 'WARNING')}>
                {data.readiness_state.replace('_', ' ')}
              </Badge>
            </div>
            <p className="mt-1 text-sm text-gray-600">
              Deterministic checks over profile data, required documents and document consistency.
            </p>
            <p className="mt-2 text-xs text-gray-500">
              Prototype readiness only — government APIs are not contacted by this check.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Readiness</p>
              <p className="text-3xl font-bold text-gray-900">{data.score}%</p>
            </div>
            <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
              <RefreshCw className={`mr-2 h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
              Recheck
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-5 pt-6">
        {!isPreSubmission && (
          <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
            This application is already in <span className="font-semibold">{data.application_status.replace('_', ' ')}</span> state; the readiness result is retained as a pre-submission reference.
          </div>
        )}

        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <p className="text-xs uppercase tracking-wide text-gray-500">Profile</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">{data.summary.profile_score}%</p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <p className="text-xs uppercase tracking-wide text-gray-500">Documents</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">
              {data.summary.documents_ready}/{data.summary.required_documents}
            </p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <p className="text-xs uppercase tracking-wide text-gray-500">Blockers</p>
            <p className={`mt-1 text-2xl font-bold ${blockingIssues.length ? 'text-red-600' : 'text-green-600'}`}>
              {blockingIssues.length}
            </p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <p className="text-xs uppercase tracking-wide text-gray-500">Warnings</p>
            <p className={`mt-1 text-2xl font-bold ${warnings.length ? 'text-amber-600' : 'text-green-600'}`}>
              {warnings.length}
            </p>
          </div>
        </div>

        <div className="space-y-2">
          {data.checks.map((check) => {
            const Icon = check.status === 'PASS' ? CheckCircle2 : check.status === 'BLOCKED' ? CircleAlert : AlertCircle
            return (
              <div key={check.key} className="flex items-start gap-3 rounded-lg border border-gray-200 p-4">
                <Icon className={`mt-0.5 h-5 w-5 ${check.status === 'PASS' ? 'text-green-600' : check.status === 'BLOCKED' ? 'text-red-600' : 'text-amber-600'}`} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold text-gray-900">{check.label}</p>
                    <Badge variant={checkVariant(check.status)}>{check.status}</Badge>
                  </div>
                  <p className="mt-1 text-sm text-gray-600">{check.message}</p>
                </div>
              </div>
            )
          })}
        </div>

        {checklist.length > 0 && (
          <div className="rounded-xl border border-gray-200">
            <button
              type="button"
              className="flex w-full items-center justify-between px-4 py-4 text-left"
              onClick={() => setExpanded((value) => !value)}
              aria-expanded={expanded}
            >
              <div className="flex items-center gap-2">
                <FileCheck2 className="h-5 w-5 text-blue-600" />
                <div>
                  <p className="font-semibold text-gray-900">Required document checklist</p>
                  <p className="text-xs text-gray-500">See exactly what is missing or needs attention.</p>
                </div>
              </div>
              <ChevronDown className={`h-5 w-5 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} />
            </button>

            {expanded && (
              <div className="divide-y divide-gray-200 border-t border-gray-200">
                {checklist.map((item) => {
                  const ready = item.status === 'READY'
                  const pending = item.status === 'VALIDATION_PENDING'
                  const invalid = item.status === 'INVALID'
                  return (
                    <div key={`${item.requirement}-${item.document_id || 'missing'}`} className="flex flex-col gap-3 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
                      <div className="flex min-w-0 items-start gap-3">
                        {ready ? (
                          <CheckCircle2 className="mt-0.5 h-5 w-5 flex-none text-green-600" />
                        ) : invalid ? (
                          <FileWarning className="mt-0.5 h-5 w-5 flex-none text-red-600" />
                        ) : (
                          <FileWarning className="mt-0.5 h-5 w-5 flex-none text-amber-600" />
                        )}
                        <div className="min-w-0">
                          <p className="font-medium text-gray-900">{item.requirement}</p>
                          <p className="mt-0.5 text-sm text-gray-500">
                            {item.file_name ? item.file_name : item.available_in_vault ? 'Available in Data Vault' : 'No matching document attached'}
                          </p>
                          {item.validation_errors?.length > 0 && (
                            <p className="mt-1 text-xs text-red-600">{item.validation_errors.join(' ')}</p>
                          )}
                          {item.candidate_documents?.length > 0 && (
                            <div className="mt-2 space-y-1.5">
                              <p className="text-xs font-medium text-gray-600">Matching project documents available</p>
                              {item.candidate_documents.map((candidate) => (
                                <div key={candidate.document_id} className="flex flex-wrap items-center gap-2 text-xs">
                                  <span className="text-gray-700">{candidate.file_name}</span>
                                  <Badge variant={candidate.status === 'VERIFIED' ? 'success' : 'warning'}>{candidate.status.replace('_', ' ')}</Badge>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handleAttach(candidate.document_id)}
                                    disabled={attachApplicationDocument.isPending}
                                    className="h-7 px-2 text-xs"
                                  >
                                    Attach
                                  </Button>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant={ready ? 'success' : invalid ? 'danger' : 'warning'}>
                          {item.status.replace('_', ' ')}
                        </Badge>
                        {item.available_in_vault && !item.file_name && (
                          <Link href="/dashboard/profile" className="text-xs font-medium text-blue-600 underline">
                            Open Data Vault
                          </Link>
                        )}
                        {pending && item.document_id && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleValidate(item.document_id)}
                            disabled={validateDocument.isPending}
                          >
                            {validateDocument.isPending ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : null}
                            Validate
                          </Button>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {(blockingIssues.length > 0 || warnings.length > 0) && (
          <div className="space-y-3">
            <p className="text-sm font-semibold uppercase tracking-wide text-gray-500">What needs attention</p>
            {[...blockingIssues, ...warnings].slice(0, 6).map((issue, index) => {
              const Icon = issueIcon(issue.severity)
              return (
                <div key={`${issue.code}-${index}`} className="flex gap-3 rounded-lg border border-gray-200 bg-white p-3">
                  <Icon className={`mt-0.5 h-5 w-5 flex-none ${issue.severity === 'BLOCKER' ? 'text-red-600' : 'text-amber-600'}`} />
                  <div>
                    <p className="text-sm font-medium text-gray-900">{issue.message}</p>
                    <p className="mt-0.5 text-xs uppercase tracking-wide text-gray-500">{issue.category}</p>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {actions.length > 0 && (
          <div className="rounded-lg border border-blue-100 bg-blue-50 p-4">
            <p className="font-semibold text-blue-900">Recommended next actions</p>
            <div className="mt-3 space-y-2">
              {actions.map((action, index) => (
                <div key={`${action.action}-${index}`} className="text-sm text-blue-900">
                  <span className="font-medium">{index + 1}. {action.action}</span>
                  {action.details?.length ? <span className="text-blue-800"> — {action.details.join(', ')}</span> : null}
                </div>
              ))}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Link href={data.project_id ? `/dashboard/${data.project_id}/documents` : '/dashboard'}>
                <Button variant="outline" size="sm">Open Project Documents</Button>
              </Link>
              <Link href="/dashboard/profile">
                <Button variant="outline" size="sm">Open Business Profile</Button>
              </Link>
            </div>
          </div>
        )}

        {error && <p className="text-sm text-red-600">{error}</p>}

        {data.can_submit ? (
          <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
            <CheckCircle2 className="h-5 w-5 flex-none" />
            All blocking pre-submission checks have passed. The application is ready for submission.
          </div>
        ) : isPreSubmission ? (
          <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            <CircleAlert className="mt-0.5 h-5 w-5 flex-none" />
            Submission is blocked until the readiness issues above are resolved.
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}

export default PreSubmissionReadiness
