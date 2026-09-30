'use client'

import React, { useCallback, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import Link from 'next/link'
import {
  CheckCircle2,
  FileText,
  Loader2,
  Rocket,
  UploadCloud,
  XCircle,
  ClipboardList,
} from 'lucide-react'
import { Button, buttonVariants } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select } from '@/components/ui/select'
import {
  useProjects,
  useCheckApplicability,
  useAddToChecklist,
  useStartChecklistApplication,
  useAttachChecklistDocument,
  useUploadDocument,
  useApplicationReadiness,
} from '@/hooks/useApi'
import PreSubmissionReadiness from '@/features/PreSubmissionReadiness'
import { apiClient } from '@/services/api'
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

interface ExploreApplyProps {
  service: any
}

export function ExploreApply({ service }: ExploreApplyProps) {
  const queryClient = useQueryClient()
  const { isOnline } = useOfflineStatus()
  const { data: projects } = useProjects()
  const [projectId, setProjectId] = useState('')
  const [applicability, setApplicability] = useState<any>(null)
  const [checklist, setChecklist] = useState<any>(null)
  const [attached, setAttached] = useState<any[]>([])
  const [error, setError] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const check = useCheckApplicability()
  const add = useAddToChecklist()
  const start = useStartChecklistApplication()
  const attach = useAttachChecklistDocument()
  const upload = useUploadDocument()
  const { data: readiness } = useApplicationReadiness(checklist?.approval_id || '')

  const projectList = Array.isArray(projects) ? projects : []

  const runCheck = async () => {
    setError('')
    if (!projectId) return
    try {
      const result = await check.mutateAsync({ serviceId: service.slug, projectId })
      setApplicability(result)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Could not check applicability')
    }
  }

  const addToChecklist = async () => {
    setError('')
    try {
      const result = await add.mutateAsync({ serviceId: service.slug, projectId })
      setChecklist(result)
      setAttached(result.attached_documents || [])
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Could not add to checklist')
    }
  }

  const startApplication = async () => {
    setError('')
    if (!checklist) return
    if (!isOnline) {
      setError('An online connection is required to start the server-side application draft. You can still review locally saved preparation drafts.')
      return
    }
    try {
      await start.mutateAsync(checklist.approval_id)
      setChecklist({ ...checklist, status: 'DRAFT' })
      queryClient.invalidateQueries({ queryKey: ['application-readiness', checklist.approval_id] })
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Could not start application')
    }
  }

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (!checklist) return
      setError('')
      for (const file of acceptedFiles) {
        try {
          const doc = await upload.mutateAsync({ projectId, file })
          await attach.mutateAsync({
            approvalId: checklist.approval_id,
            documentId: doc.id,
          })
          setAttached((prev) => [...prev, { ...doc, id: doc.id, file_name: doc.file_name, status: doc.status }])
        } catch (e: any) {
          setError(e.response?.data?.detail || 'Upload failed')
        }
      }
      queryClient.invalidateQueries({ queryKey: ['explore-service-documents'] })
      if (checklist?.approval_id) {
        queryClient.invalidateQueries({ queryKey: ['application-readiness', checklist.approval_id] })
      }
    },
    [checklist, projectId, upload, attach, isOnline, queryClient],
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg'],
      'application/msword': ['.doc', '.docx'],
    },
    maxSize: 50 * 1024 * 1024,
    disabled: !isOnline,
  })

  const submitApplication = async () => {
    setError('')
    if (!checklist) return
    if (!isOnline) {
      setError('Submission requires an online connection. Your draft remains safely stored on this device.')
      return
    }
    try {
      const latestReadiness = await apiClient.getApplicationReadiness(checklist.approval_id)
      queryClient.setQueryData(['application-readiness', checklist.approval_id], latestReadiness)
      if (!latestReadiness.can_submit) {
        setError('Resolve the pre-submission readiness checks before submitting.')
        return
      }
      await apiClient.submitApplication(checklist.approval_id)
      setSubmitted(true)
      setChecklist({ ...checklist, status: 'SUBMITTED' })
      queryClient.invalidateQueries({ queryKey: ['application-readiness', checklist.approval_id] })
    } catch (e: any) {
      const detail = e.response?.data?.detail
      if (detail?.readiness) {
        queryClient.setQueryData(['application-readiness', checklist.approval_id], detail.readiness)
      }
      setError(detail?.message || detail || 'Could not submit application')
    }
  }

  const status = checklist?.status || 'NOT_STARTED'
  const canStart = status === 'NOT_STARTED'
  const canSubmit = status === 'DRAFT'

  return (
    <div className="space-y-6">
      {service.application_mode === 'REDIRECT' && !service.is_demo && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-5">
          <p className="text-sm text-yellow-800">
            This service is handled on an external government portal. We help you prepare the
            documents, then you complete the submission there.
          </p>
          {service.external_portal_url && (
            <a
              href={service.external_portal_url}
              target="_blank"
              rel="noreferrer"
              className={buttonVariants({ variant: 'outline', size: 'sm', className: 'mt-3' })}
            >
              Open portal →
            </a>
          )}
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-5">
        <div className="flex items-center gap-2">
          <ClipboardList className="w-5 h-5 text-blue-600" />
          <h3 className="font-semibold text-gray-900">Apply for this service</h3>
        </div>

        <div>
          <label className="text-sm font-medium text-gray-700">Choose a project</label>
          <div className="flex flex-col sm:flex-row gap-2 sm:items-start">
            <Select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              <option value="">Select project...</option>
              {projectList.map((p: any) => (
                <option key={p.id} value={p.id}>
                  {p.name} — {p.company_name}
                </option>
              ))}
            </Select>
            <Button variant="outline" onClick={runCheck} disabled={!projectId || !isOnline || check.isPending} className="shrink-0">
              {check.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Check Applicability'}
            </Button>
          </div>
          {projectList.length === 0 && (
            <p className="mt-2 text-sm text-gray-500">
              You need a project first.{' '}
              <Link href="/dashboard/new-project" className="text-blue-600 underline">
                Create one
              </Link>{' '}
              to start applying.
            </p>
          )}
        </div>

        {applicability && (
          <div
            className={`rounded-lg p-4 border ${
              applicability.status === 'APPLICABLE'
                ? 'bg-green-50 border-green-200'
                : applicability.status === 'NOT_APPLICABLE'
                  ? 'bg-red-50 border-red-200'
                  : 'bg-gray-50 border-gray-200'
            }`}
          >
            <div className="flex items-center gap-2">
              {applicability.status === 'APPLICABLE' ? (
                <CheckCircle2 className="w-5 h-5 text-green-600" />
              ) : applicability.status === 'NOT_APPLICABLE' ? (
                <XCircle className="w-5 h-5 text-red-600" />
              ) : (
                <FileText className="w-5 h-5 text-gray-500" />
              )}
              <span className="font-medium text-gray-900">{applicability.status.replace('_', ' ')}</span>
            </div>
            <p className="mt-2 text-sm text-gray-700">{applicability.reason}</p>
            {applicability.matched_conditions.length > 0 && (
              <ul className="mt-2 space-y-1 text-sm text-green-700">
                {applicability.matched_conditions.map((m: string, i: number) => (
                  <li key={i}>· {m}</li>
                ))}
              </ul>
            )}
            {applicability.failed_conditions.length > 0 && (
              <ul className="mt-2 space-y-1 text-sm text-red-700">
                {applicability.failed_conditions.map((f: string, i: number) => (
                  <li key={i}>· {f}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        {!checklist && (
          <Button onClick={addToChecklist} disabled={!projectId || !isOnline || add.isPending}>
            {add.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Add to my checklist'}
          </Button>
        )}

        {error && <p className="text-sm text-red-600">{error}</p>}

        {checklist && (
          <div className="space-y-4 border-t border-gray-200 pt-5">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <div className="min-w-0">
                <p className="font-medium text-gray-900">Application: {checklist.name}</p>
                <p className="text-sm text-gray-500">{checklist.department}</p>
              </div>
              <Badge variant={statusVariant(status)} className="w-fit">{status.replace('_', ' ')}</Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {checklist.required_documents && checklist.required_documents.length > 0 && (
                <div className="rounded-lg bg-gray-50 border border-gray-200 p-4">
                  <p className="text-sm font-semibold text-gray-900 mb-2">Required documents</p>
                  <ul className="space-y-1 text-sm text-gray-700">
                    {checklist.required_documents.map((r: any, i: number) => (
                      <li key={i} className="flex items-center gap-2">
                        {attached.some((d: any) =>
                          (d.document_type || '').toLowerCase().includes(r.document_type.toLowerCase()),
                        ) ? (
                          <CheckCircle2 className="w-4 h-4 text-green-600" />
                        ) : (
                          <FileText className="w-4 h-4 text-gray-400" />
                        )}
                        {r.document_type}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="rounded-lg bg-gray-50 border border-gray-200 p-4">
                <p className="text-sm font-semibold text-gray-900 mb-2">Attached documents</p>
                {attached.length === 0 ? (
                  <p className="text-sm text-gray-500">None yet.</p>
                ) : (
                  <ul className="space-y-1 text-sm text-gray-700">
                    {attached.map((d: any) => (
                      <li key={d.id} className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-gray-400" />
                        {d.file_name}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {checklist && (
              <PreSubmissionReadiness
                applicationId={checklist.approval_id}
                applicationStatus={status}
              />
            )}

            <div className="flex flex-wrap gap-2">
              {canStart && (
                <Button onClick={startApplication} disabled={start.isPending || !isOnline}>
                  {start.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Start Application'}
                </Button>
              )}
              {status === 'DRAFT' && (
                <Link
                  href={`/dashboard/applications/${checklist.approval_id}/prepare`}
                  className={buttonVariants({ variant: 'outline' })}
                >
                  Prepare application →
                </Link>
              )}
            </div>

            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition ${
                isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400'
              }`}
            >
              <input {...getInputProps()} />
              <UploadCloud className="w-6 h-6 mx-auto text-blue-600" />
              <p className="mt-2 text-sm text-gray-700 font-medium">
                Drag & drop {status === 'SUBMITTED' ? 'documents' : 'documents here'}
              </p>
              <p className="text-xs text-gray-500">Uploaded documents are attached to this application</p>
            </div>

            {submitted && (
              <div className="rounded-lg bg-green-50 border border-green-200 p-4">
                <p className="text-sm text-green-800">
                  Application submitted. You can track it under
                </p>
                <Link
                  href="/dashboard/applications"
                  className="text-sm font-medium text-blue-600 underline"
                >
                  Applications →
                </Link>
              </div>
            )}

            {canSubmit && (
              <Button onClick={submitApplication} className="w-full" disabled={readiness?.can_submit !== true || start.isPending}>
                <Rocket className="w-4 h-4 mr-2" />
                Submit Application
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}