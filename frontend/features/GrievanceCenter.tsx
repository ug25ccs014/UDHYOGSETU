'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { AlertCircle, ArrowUpRight, CheckCircle2, Clock3, MessageSquareWarning, Send, ShieldAlert } from 'lucide-react'
import { useSearchParams } from 'next/navigation'
import { useQueryClient } from '@tanstack/react-query'
import { useApplications, useCreateGrievance, useEscalateGrievance, useGrievanceOfficers, useGrievances, useTransitionGrievance } from '@/hooks/useApi'
import { getSessionUser } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import type { Grievance } from '@/types'

function statusVariant(status: string): 'success' | 'warning' | 'info' | 'danger' | 'default' | 'outline' {
  switch (status) {
    case 'RESOLVED':
    case 'CLOSED':
      return 'success'
    case 'ESCALATED':
      return 'danger'
    case 'ACKNOWLEDGED':
    case 'IN_REVIEW':
      return 'info'
    case 'OPEN':
      return 'warning'
    default:
      return 'outline'
  }
}

function priorityVariant(priority: string): 'danger' | 'warning' | 'default' {
  return priority === 'HIGH' ? 'danger' : priority === 'MEDIUM' ? 'warning' : 'default'
}

export default function GrievanceCenter() {
  const params = useSearchParams()
  const queryApplicationId = params.get('applicationId') || ''
  const user = getSessionUser()
  const officerMode = ['OFFICER', 'ADMIN'].includes((user?.role || '').toUpperCase())
  const queryClient = useQueryClient()
  const grievancesQuery = useGrievances()
  const applicationsQuery = useApplications()
  const create = useCreateGrievance()
  const transition = useTransitionGrievance()
  const escalate = useEscalateGrievance()
  const grievanceOfficersQuery = useGrievanceOfficers(officerMode)

  const grievances: Grievance[] = grievancesQuery.data?.grievances || []
  const applications: any[] = applicationsQuery.data?.applications || []
  const grievanceOfficers: any[] = grievanceOfficersQuery.data?.officers || []
  const initialApplication = useMemo(
    () => applications.find((application) => application.application_id === queryApplicationId),
    [applications, queryApplicationId],
  )

  const [applicationId, setApplicationId] = useState(queryApplicationId)
  const [category, setCategory] = useState('Application Delay')
  const [priority, setPriority] = useState('MEDIUM')
  const [subject, setSubject] = useState('Application requires attention')
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [actionNote, setActionNote] = useState<Record<string, string>>({})

  const summary = grievancesQuery.data?.summary || {
    total: grievances.length,
    open: grievances.filter((g) => ['OPEN', 'ACKNOWLEDGED', 'IN_REVIEW', 'ESCALATED'].includes(g.status)).length,
    escalated: grievances.filter((g) => g.status === 'ESCALATED').length,
    resolved: grievances.filter((g) => g.status === 'RESOLVED').length,
    overdue_targets: 0,
  }

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['grievances'] })
    queryClient.invalidateQueries({ queryKey: ['grievance-summary'] })
    queryClient.invalidateQueries({ queryKey: ['applications'] })
  }

  const submit = async () => {
    setError('')
    setSuccess('')
    try {
      const selected = applications.find((a) => a.application_id === applicationId)
      const result = await create.mutateAsync({
        application_id: applicationId || undefined,
        project_id: selected?.project_id || undefined,
        category,
        subject,
        description,
        priority,
      })
      setSuccess(`Grievance ${result.id.slice(0, 8)} has been recorded.`)
      setDescription('')
      refresh()
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Could not submit grievance')
    }
  }

  const act = async (g: Grievance, status: string) => {
    setError('')
    try {
      await transition.mutateAsync({
        grievanceId: g.id,
        payload: {
          to_status: status,
          note: actionNote[g.id] || undefined,
          resolution_note: status === 'RESOLVED' ? actionNote[g.id] : undefined,
        },
      })
      setActionNote((prev) => ({ ...prev, [g.id]: '' }))
      setExpanded(null)
      refresh()
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Could not update grievance')
    }
  }

  const doEscalate = async (g: Grievance) => {
    setError('')
    const reason = actionNote[g.id]?.trim()
    if (!reason) {
      setError('Add an escalation reason before escalating.')
      return
    }
    try {
      await escalate.mutateAsync({ grievanceId: g.id, reason })
      setActionNote((prev) => ({ ...prev, [g.id]: '' }))
      refresh()
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Could not escalate grievance')
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-3">
          <MessageSquareWarning className="h-7 w-7 text-blue-600" />
          <h1 className="text-3xl font-bold text-gray-900">Grievance & Escalation Center</h1>
        </div>
        <p className="mt-1 text-gray-600">Record application issues, follow their resolution path, and use an auditable escalation workflow.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {[
          ['Total', summary.total, 'text-blue-600'],
          ['Open', summary.open, 'text-amber-600'],
          ['Escalated', summary.escalated, 'text-red-600'],
          ['Resolved', summary.resolved, 'text-green-600'],
          ['Target overdue', summary.overdue_targets, 'text-orange-600'],
        ].map(([label, value, color]) => (
          <Card key={String(label)}><CardContent className="p-4"><p className="text-xs text-gray-500">{label}</p><p className={`mt-1 text-2xl font-bold ${color}`}>{value}</p></CardContent></Card>
        ))}
      </div>

      {!officerMode && (
        <Card className="border-blue-200">
          <CardHeader><CardTitle className="text-lg">Raise a grievance</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="md:col-span-2">
                <label className="text-sm font-medium text-gray-700">Application (optional)</label>
                <Select value={applicationId} onChange={(e) => setApplicationId(e.target.value)}>
                  <option value="">General project issue</option>
                  {applications.map((a) => <option key={a.application_id} value={a.application_id}>{a.approval_name} — {a.project_name}</option>)}
                </Select>
                {initialApplication && <p className="mt-1 text-xs text-gray-500">Opened from {initialApplication.approval_name}.</p>}
              </div>
              <div><label className="text-sm font-medium text-gray-700">Priority</label><Select value={priority} onChange={(e) => setPriority(e.target.value)}><option value="LOW">Low</option><option value="MEDIUM">Medium</option><option value="HIGH">High</option></Select></div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div><label className="text-sm font-medium text-gray-700">Category</label><Select value={category} onChange={(e) => setCategory(e.target.value)}><option>Application Delay</option><option>No Status Update</option><option>Unresolved Query</option><option>Inspection Issue</option><option>SLA Concern</option><option>Other</option></Select></div>
              <div className="md:col-span-2"><label className="text-sm font-medium text-gray-700">Subject</label><input value={subject} onChange={(e) => setSubject(e.target.value)} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" maxLength={255} /></div>
            </div>
            <div><label className="text-sm font-medium text-gray-700">Description</label><Textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Describe what happened, what you expected, and what action you need." rows={5} /></div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            {success && <p className="text-sm text-green-700">{success}</p>}
            <div className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-600"><span>UDYOGSETU records the grievance locally. External authority escalation requires an authorized integration.</span><Button onClick={submit} disabled={create.isPending || description.trim().length < 10}><Send className="mr-2 h-4 w-4" />Submit grievance</Button></div>
          </CardContent>
        </Card>
      )}

      <div className="space-y-4">
        {grievances.length === 0 ? (
          <Card><CardContent className="py-12 text-center text-gray-500">No grievances have been recorded yet.</CardContent></Card>
        ) : grievances.map((g) => {
          const isOpen = expanded === g.id
          return (
            <Card key={g.id} className="overflow-hidden">
              <CardHeader className="pb-3">
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2"><CardTitle className="text-base">{g.subject}</CardTitle><Badge variant={statusVariant(g.status)}>{g.status.replace('_', ' ')}</Badge><Badge variant={priorityVariant(g.priority)}>{g.priority}</Badge>{g.escalation_level > 0 && <Badge variant="danger">Escalation {g.escalation_level}</Badge>}</div>
                    <p className="mt-1 text-sm text-gray-600">{g.project_name} {g.application_id ? `· ${g.application_id}` : ''} {g.department ? `· ${g.department}` : ''}</p>
                  </div>
                  <Button size="sm" variant="outline" onClick={() => setExpanded(isOpen ? null : g.id)}>{isOpen ? 'Hide details' : 'View details'} <ArrowUpRight className="ml-1 h-4 w-4" /></Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                  <div className="rounded-lg bg-gray-50 p-3"><p className="text-xs text-gray-500">Raised</p><p className="mt-1 font-medium text-gray-900">{new Date(g.created_at).toLocaleString()}</p></div>
                  <div className="rounded-lg bg-gray-50 p-3"><p className="text-xs text-gray-500">Response target</p><p className="mt-1 font-medium text-gray-900">{g.response_target_at ? new Date(g.response_target_at).toLocaleDateString() : '—'}</p></div>
                  <div className="rounded-lg bg-gray-50 p-3"><p className="text-xs text-gray-500">Assigned</p><p className="mt-1 font-medium text-gray-900">{g.assigned_officer_name || 'Awaiting assignment'}</p></div>
                </div>

                {isOpen && (
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 border-t border-gray-200 pt-4">
                    <div className="lg:col-span-2 space-y-4">
                      <div><p className="text-sm font-semibold text-gray-900">Issue</p><p className="mt-1 text-sm whitespace-pre-line text-gray-700">{g.description}</p></div>
                      {g.sla_context && <div className="rounded-lg border border-amber-200 bg-amber-50 p-4"><div className="flex gap-2"><ShieldAlert className="h-4 w-4 mt-0.5 text-amber-700" /><div><p className="text-sm font-semibold text-amber-950">Application SLA context</p><p className="mt-1 text-sm text-amber-900">{g.sla_context.sla?.status || 'Not started'} · {g.sla_context.key_risk_factors?.join(' · ') || 'No recorded factors'}</p></div></div></div>}
                      <div><p className="text-sm font-semibold text-gray-900 mb-2">Timeline</p><div className="space-y-3">{g.events.map((event) => <div key={event.id} className="flex gap-3"><div className="mt-1 h-2 w-2 rounded-full bg-blue-500 shrink-0" /><div><p className="text-sm text-gray-900">{event.event_type.replace(/_/g, ' ')}</p><p className="text-xs text-gray-500">{event.actor_name || 'System'} · {event.created_at ? new Date(event.created_at).toLocaleString() : ''}</p>{event.note && <p className="mt-1 text-sm text-gray-600">{event.note}</p>}</div></div>)}</div></div>
                    </div>
                    <div className="space-y-3">
                      {officerMode ? (
                        <>
                          <p className="text-sm font-semibold text-gray-900">Officer actions</p>
                          {g.assigned_officer_id !== undefined && (
                            <div>
                              <label className="text-xs font-medium text-gray-600">Assign officer</label>
                              <Select
                                value={g.assigned_officer_id || ''}
                                onChange={async (e) => {
                                  setError('')
                                  try {
                                    await transition.mutateAsync({ grievanceId: g.id, payload: { to_status: g.status, assigned_officer_id: e.target.value || undefined } })
                                    refresh()
                                  } catch (err: any) {
                                    setError(err.response?.data?.detail || 'Could not assign officer')
                                  }
                                }}
                              >
                                <option value="">Unassigned</option>
                                {grievanceOfficers.map((officer) => <option key={officer.id} value={officer.id}>{officer.name}</option>)}
                              </Select>
                            </div>
                          )}
                          <Textarea value={actionNote[g.id] || ''} onChange={(e) => setActionNote((prev) => ({ ...prev, [g.id]: e.target.value }))} placeholder="Response, escalation reason, or resolution explanation" rows={4} />
                          <div className="flex flex-wrap gap-2">
                            {g.status === 'OPEN' && <Button size="sm" onClick={() => act(g, 'ACKNOWLEDGED')}>Acknowledge</Button>}
                            {['OPEN', 'ACKNOWLEDGED'].includes(g.status) && <Button size="sm" variant="outline" onClick={() => act(g, 'IN_REVIEW')}>Start review</Button>}
                            {g.status !== 'ESCALATED' && !['RESOLVED', 'CLOSED', 'REJECTED'].includes(g.status) && <Button size="sm" variant="danger" onClick={() => doEscalate(g)}>Escalate</Button>}
                            {g.status === 'ESCALATED' && g.escalation_level < 2 && <Button size="sm" variant="danger" onClick={() => doEscalate(g)}>Escalate to next level</Button>}
                            {!['RESOLVED', 'CLOSED', 'REJECTED'].includes(g.status) && <Button size="sm" variant="outline" onClick={() => act(g, 'RESOLVED')}><CheckCircle2 className="mr-1 h-4 w-4" />Resolve</Button>}
                            {!['RESOLVED', 'CLOSED', 'REJECTED'].includes(g.status) && g.status !== 'OPEN' && <Button size="sm" variant="outline" onClick={() => act(g, 'REJECTED')}>Reject</Button>}
                          </div>
                        </>
                      ) : (
                        !['RESOLVED', 'CLOSED', 'REJECTED'].includes(g.status) && <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 space-y-3"><div className="flex gap-2"><AlertCircle className="h-4 w-4 mt-0.5 text-amber-700" /><p className="text-sm text-amber-900">Requesting escalation creates an auditable case event; it does not transmit a grievance to a government authority.</p></div><Textarea value={actionNote[g.id] || ''} onChange={(e) => setActionNote((prev) => ({ ...prev, [g.id]: e.target.value }))} placeholder="Why does this case need higher-level attention?" rows={3} /><Button size="sm" variant="danger" onClick={() => doEscalate(g)} disabled={escalate.isPending || g.escalation_level >= 2 || !(actionNote[g.id] || '').trim()}>Request escalation</Button></div>
                      )}
                      {g.status === 'RESOLVED' && !officerMode && <Button size="sm" onClick={() => act(g, 'CLOSED')}>Confirm closure</Button>}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>

      <div className="rounded-lg border border-blue-100 bg-blue-50 p-4 text-sm text-blue-900 flex gap-2"><Clock3 className="h-4 w-4 mt-0.5" /><span>Response-target dates in this prototype are internal service targets based on grievance priority, not statutory government timelines.</span></div>
    </div>
  )
}
