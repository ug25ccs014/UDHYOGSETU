'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useQueryClient } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import {
  AlertCircle,
  CheckCircle2,
  FileCheck2,
  FileText,
  Info,
  Loader2,
  Paperclip,
  Send,
  Sparkles,
  UploadCloud,
} from 'lucide-react'
import {
  useApplicationQueryCenter,
  useAttachApplicationDocument,
  useDetachApplicationDocument,
  useSaveApplicationQueryResponse,
  useSubmitApplicationQueryResponse,
  useUploadDocument,
} from '@/hooks/useApi'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import type { ApplicationQueryCenter as QueryCenterResponse } from '@/types'
import { useOfflineStatus } from '@/hooks/useOfflineStatus'

interface Props {
  applicationId: string
  compact?: boolean
}

function statusVariant(status?: string | null): 'success' | 'warning' | 'info' | 'outline' | 'danger' {
  switch (status) {
    case 'SUBMITTED':
      return 'success'
    case 'READY':
      return 'info'
    case 'DRAFT':
      return 'warning'
    default:
      return 'outline'
  }
}

export function QueryResolutionCenter({ applicationId, compact = false }: Props) {
  const queryClient = useQueryClient()
  const { data, isLoading, isError } = useApplicationQueryCenter(applicationId)
  const save = useSaveApplicationQueryResponse()
  const submit = useSubmitApplicationQueryResponse()
  const upload = useUploadDocument()
  const attach = useAttachApplicationDocument()
  const detach = useDetachApplicationDocument()
  const { isOnline } = useOfflineStatus()
  const [response, setResponse] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [busyDocumentId, setBusyDocumentId] = useState<string | null>(null)

  const center = data as QueryCenterResponse | undefined

  useEffect(() => {
    if (center?.response_draft !== undefined) {
      setResponse(center.response_draft || '')
    }
  }, [center?.response_draft, center?.query_id])

  const attachedIds = useMemo(
    () => new Set((center?.attached_documents || []).map((doc) => doc.document_id)),
    [center?.attached_documents],
  )

  const attachDocument = async (documentId: string) => {
    setBusyDocumentId(documentId)
    setError('')
    setMessage('')
    try {
      await attach.mutateAsync({ applicationId, documentId })
      setMessage('Document attached to the query response package.')
      queryClient.invalidateQueries({ queryKey: ['application-query-center', applicationId] })
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Could not attach the document.')
    } finally {
      setBusyDocumentId(null)
    }
  }

  const detachDocument = async (documentId: string) => {
    setBusyDocumentId(documentId)
    setError('')
    try {
      await detach.mutateAsync({ applicationId, documentId })
      setMessage('Document removed from the response package.')
      queryClient.invalidateQueries({ queryKey: ['application-query-center', applicationId] })
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Could not remove the document.')
    } finally {
      setBusyDocumentId(null)
    }
  }

  const onDrop = useCallback(async (files: File[]) => {
    if (!center?.project_id || !center.can_save || !isOnline || files.length === 0) return
    setUploading(true)
    setError('')
    setMessage('')
    try {
      for (const file of files) {
        const document = await upload.mutateAsync({ projectId: center.project_id, file })
        await attach.mutateAsync({ applicationId, documentId: document.id })
      }
      setMessage('Uploaded document(s) and added them to the response package.')
      await queryClient.invalidateQueries({ queryKey: ['application-query-center', applicationId] })
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Could not upload the document.')
    } finally {
      setUploading(false)
    }
  }, [applicationId, attach, center?.can_save, center?.project_id, isOnline, queryClient, upload])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
    maxSize: 50 * 1024 * 1024,
    disabled: !isOnline,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg', '.webp'],
      'application/msword': ['.doc', '.docx'],
      'text/plain': ['.txt'],
    },
  })

  const saveDraft = async (ready = false) => {
    if (!center?.query_id) return
    setError('')
    setMessage('')
    try {
      await save.mutateAsync({
        applicationId,
        payload: { query_id: center.query_id, response_text: response, ready },
      })
      setMessage(ready ? 'Response marked ready for submission.' : 'Response draft saved.')
      queryClient.invalidateQueries({ queryKey: ['application-query-center', applicationId] })
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Could not save the response.')
    }
  }

  const submitResponse = async () => {
    if (!center?.query_id) return
    if (!isOnline) {
      setError('Submitting a query response requires an online connection. Your response text remains in the form until connectivity returns.')
      return
    }
    setError('')
    setMessage('')
    try {
      const result = await submit.mutateAsync({
        applicationId,
        payload: { query_id: center.query_id, response_text: response },
      })
      setResponse(result.response_draft || response)
      setMessage('Response recorded. No external government API was called.')
      await queryClient.invalidateQueries({ queryKey: ['application-query-center', applicationId] })
      await queryClient.invalidateQueries({ queryKey: ['application', applicationId] })
      await queryClient.invalidateQueries({ queryKey: ['application-transitions', applicationId] })
      await queryClient.invalidateQueries({ queryKey: ['applications'] })
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Could not record the response.')
    }
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 py-10 text-sm text-gray-600">
          <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
          Loading query-resolution workspace...
        </CardContent>
      </Card>
    )
  }

  if (isError || !center) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-gray-600">
          Query-resolution workspace is temporarily unavailable.
        </CardContent>
      </Card>
    )
  }

  if (!center.query_present) {
    return (
      <Card className="border-slate-200">
        <CardContent className="flex items-start gap-3 py-8">
          <CheckCircle2 className="mt-0.5 h-5 w-5 text-teal-600" />
          <div>
            <p className="font-semibold text-gray-900">No open government query</p>
            <p className="mt-1 text-sm text-gray-600">This application currently has no stored query requiring an applicant response.</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const readOnly = center.status === 'SUBMITTED' || !center.can_save
  const submitted = center.status === 'SUBMITTED'

  return (
    <div className={compact ? 'space-y-4' : 'space-y-6'}>
      <Card className="border-amber-200">
        <CardHeader className="pb-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="flex items-center gap-2 text-sm font-medium text-amber-800">
                <AlertCircle className="h-4 w-4" />
                Query & Response Center
              </div>
              <CardTitle className="mt-1 text-xl">Department query requires your attention</CardTitle>
              <p className="mt-1 text-sm text-gray-600">
                Review what was asked, attach supporting evidence, then save or record your response.
              </p>
            </div>
            <Badge variant={statusVariant(center.status)}>{center.status === 'SUBMITTED' ? 'Response recorded' : center.status}</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">Original government query</p>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-gray-900">{center.query}</p>
          </div>
          <div className="rounded-xl border border-blue-100 bg-blue-50 p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-blue-900">
              <Sparkles className="h-4 w-4" /> AI explanation
            </div>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-blue-950">{center.explanation}</p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs text-gray-600">
            <Badge variant="outline">System: {center.government.system || 'Not connected'}</Badge>
            <Badge variant="outline">Source: Prototype / local record</Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">What you need to address</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {center.required_evidence.map((item, index) => (
            <div key={`${item.label}-${index}`} className={`rounded-xl border p-4 ${item.satisfied ? 'border-teal-100 bg-teal-50' : 'border-red-200 bg-red-50'}`}>
              <div className="flex items-start gap-3">
                {item.satisfied ? <CheckCircle2 className="mt-0.5 h-5 w-5 text-teal-600" /> : <AlertCircle className="mt-0.5 h-5 w-5 text-red-600" />}
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-gray-900">{item.label}</p>
                  <p className="mt-1 text-xs text-gray-600">
                    {item.satisfied ? `${item.matched_documents.length} supporting document(s) identified in your workspace.` : 'No matching supporting document was identified yet.'}
                  </p>
                  {item.matched_documents.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {item.matched_documents.map((doc) => (
                        <Badge key={doc.document_id} variant="outline">{doc.file_name}</Badge>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base"><FileCheck2 className="h-5 w-5 text-blue-600" /> Response evidence package</CardTitle>
          <p className="text-sm text-gray-600">Attach existing project documents or upload new evidence. Files are reused through the existing application-document system.</p>
        </CardHeader>
        <CardContent className="space-y-4">
          {center.attached_documents.length > 0 && (
            <div className="space-y-2">
              {center.attached_documents.map((doc) => (
                <div key={doc.document_id} className="flex items-center justify-between gap-3 rounded-xl border border-teal-100 bg-teal-50 p-3">
                  <div className="flex min-w-0 items-center gap-3">
                    <Paperclip className="h-4 w-4 shrink-0 text-teal-700" />
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-gray-900">{doc.file_name}</p>
                      <p className="text-xs text-gray-600">{doc.document_type || 'Document'} · {doc.status}</p>
                    </div>
                  </div>
                  {!readOnly && (
                    <Button size="sm" variant="outline" disabled={!isOnline || busyDocumentId === doc.document_id} onClick={() => detachDocument(doc.document_id)}>
                      Remove
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}

          {!readOnly && center.available_documents.filter((doc) => !attachedIds.has(doc.document_id)).length > 0 && (
            <div>
              <p className="mb-2 text-sm font-semibold text-gray-900">Use an existing project document</p>
              <div className="space-y-2">
                {center.available_documents.filter((doc) => !attachedIds.has(doc.document_id)).map((doc) => (
                  <div key={doc.document_id} className="flex items-center justify-between gap-3 rounded-xl border border-gray-200 p-3">
                    <div className="flex min-w-0 items-center gap-3">
                      <FileText className="h-4 w-4 shrink-0 text-gray-400" />
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-gray-900">{doc.file_name}</p>
                        <p className="text-xs text-gray-600">{doc.document_type || 'Document'} · {doc.status}</p>
                      </div>
                    </div>
                    <Button size="sm" variant="outline" disabled={!isOnline || busyDocumentId === doc.document_id} onClick={() => attachDocument(doc.document_id)}>
                      {busyDocumentId === doc.document_id ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Attach'}
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {!readOnly && (
            <div
              {...getRootProps()}
              className={`rounded-xl border-2 border-dashed p-6 text-center transition ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400'}`}
            >
              <input {...getInputProps()} />
              {uploading ? <Loader2 className="mx-auto h-6 w-6 animate-spin text-blue-600" /> : <UploadCloud className="mx-auto h-6 w-6 text-blue-600" />}
              <p className="mt-2 text-sm font-medium text-gray-800">Upload supporting evidence</p>
              <p className="mt-1 text-xs text-gray-500">PDF, image, DOC/DOCX or TXT · max 50 MB each</p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Prepare your response</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-950">
            <div className="flex items-start gap-2"><Sparkles className="mt-0.5 h-4 w-4 shrink-0" /><div><p className="font-semibold">AI-assisted draft</p><p className="mt-1">The draft below is based only on the stored query and documents identified in this workspace. Review it before recording a response.</p></div></div>
          </div>

          {!response && center.suggested_response && !readOnly && (
            <Button variant="outline" onClick={() => setResponse(center.suggested_response || '')}>Use suggested response</Button>
          )}

          <Textarea
            value={response}
            onChange={(e) => setResponse(e.target.value)}
            placeholder="Write your response to the department query..."
            rows={9}
            disabled={readOnly}
          />

          {center.submitted_response && (
            <div className="rounded-xl border border-teal-100 bg-teal-50 p-4 text-sm text-teal-600">
              <p className="font-semibold">Response recorded on {center.submitted_at ? new Date(center.submitted_at).toLocaleString() : 'the application'}.</p>
              <p className="mt-2 whitespace-pre-wrap">{center.submitted_response}</p>
            </div>
          )}

          {message && <p className="text-sm text-teal-700">{message}</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}

          {!readOnly && (
            <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
              <Button variant="outline" onClick={() => saveDraft(false)} disabled={!isOnline || !response.trim() || save.isPending || submit.isPending}>
                {save.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Save draft
              </Button>
              <Button variant="outline" onClick={() => saveDraft(true)} disabled={!isOnline || !response.trim() || save.isPending || submit.isPending}>
                Mark ready
              </Button>
              <Button onClick={submitResponse} disabled={!isOnline || !response.trim() || submit.isPending}>
                {submit.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
                Record response
              </Button>
            </div>
          )}

          <div className="flex items-start gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
            <Info className="mt-0.5 h-4 w-4 shrink-0" />
            <p>{center.disclaimer || 'AI assistance is advisory. Review all content before responding to an authority. No external government API is called from this workspace.'}</p>
          </div>

          {center.regulatory_context.length > 0 && (
            <div className="border-t border-gray-200 pt-4">
              <p className="text-sm font-semibold text-gray-900">Regulatory sources used for grounding</p>
              <div className="mt-2 space-y-2">
                {center.regulatory_context.map((source, index) => (
                  <div key={`${source.title || 'source'}-${index}`} className="rounded-xl border border-gray-200 p-3 text-sm">
                    <p className="font-medium text-gray-900">{source.title || 'Regulatory source'}</p>
                    {source.url && <Link className="mt-1 block truncate text-xs text-blue-600 hover:underline" href={source.url} target="_blank">{source.url}</Link>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default QueryResolutionCenter
