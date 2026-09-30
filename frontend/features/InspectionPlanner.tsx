'use client'

import { useLanguage } from '@/lib/language'
import PageHeader from '@/components/PageHeader'
import { useMemo, useState } from 'react'
import Link from 'next/link'
import {
  AlertCircle,
  CalendarDays,
  CheckCircle2,
  Clock3,
  MapPin,
  RefreshCw,
  ShieldCheck,
  Users,
} from 'lucide-react'
import { getSessionUser } from '@/lib/auth'
import {
  useInspectionCoordinationSuggestions,
  useInspectionOfficers,
  useInspections,
  useScheduleInspection,
  useUpdateInspection,
} from '@/hooks/useApi'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { InspectionVisit } from '@/types'

function localInputValue(date: Date) {
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function statusVariant(status: string): 'success' | 'warning' | 'info' | 'outline' | 'danger' {
  switch (status) {
    case 'COMPLETED':
      return 'success'
    case 'SCHEDULED':
      return 'info'
    case 'NO_SHOW':
      return 'warning'
    case 'CANCELLED':
      return 'danger'
    default:
      return 'outline'
  }
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString([], {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function VisitCard({ visit, officerMode, onStatus, onReschedule, onChecklistToggle, editing, editStart, editEnd, setEditStart, setEditEnd, onSaveReschedule, onCancelReschedule }: {
  visit: InspectionVisit
  officerMode: boolean
  onStatus?: (visitId: string, status: string) => void
  onReschedule?: (visit: InspectionVisit) => void
  onChecklistToggle?: (visit: InspectionVisit, itemId: string) => void
  editing?: boolean
  editStart?: string
  editEnd?: string
  setEditStart?: (value: string) => void
  setEditEnd?: (value: string) => void
  onSaveReschedule?: () => void
  onCancelReschedule?: () => void
}) {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
          <div>
            <CardTitle className="text-base">
              {visit.coordinated ? 'Coordinated Site Visit' : 'Inspection Visit'}
            </CardTitle>
            <p className="mt-1 text-sm text-gray-600">{visit.project_name || visit.company_name || 'Project'}</p>
          </div>
          <Badge variant={statusVariant(visit.status)}>{visit.status.replace('_', ' ')}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
          <div className="flex items-start gap-2 text-gray-700">
            <CalendarDays className="w-4 h-4 mt-0.5 text-blue-600" />
            <span>{formatDateTime(visit.scheduled_start)}</span>
          </div>
          <div className="flex items-start gap-2 text-gray-700">
            <Clock3 className="w-4 h-4 mt-0.5 text-blue-600" />
            <span>{formatDateTime(visit.scheduled_end)} end</span>
          </div>
          <div className="flex items-start gap-2 text-gray-700 sm:col-span-2">
            <MapPin className="w-4 h-4 mt-0.5 text-blue-600" />
            <span>{visit.location || 'Location to be confirmed'}</span>
          </div>
        </div>

        {visit.assigned_officer_name && (
          <div className="rounded-xl bg-gray-50 border border-gray-200 p-3 text-sm">
            <span className="text-gray-500">Assigned officer: </span>
            <span className="font-medium text-gray-900">{visit.assigned_officer_name}</span>
          </div>
        )}

        <div>
          <p className="text-sm font-semibold text-gray-900 mb-2">Applications covered</p>
          <div className="space-y-2">
            {visit.approvals.map((approval) => (
              <div key={approval.id} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 rounded-xl border border-gray-100 p-3">
                <div>
                  <p className="text-sm font-medium text-gray-900">{approval.name}</p>
                  <p className="text-xs text-gray-500">{approval.department} · {approval.application_id}</p>
                </div>
                <Badge variant="outline">{approval.status.replace('_', ' ')}</Badge>
              </div>
            ))}
          </div>
        </div>

        {visit.checklist.length > 0 && (
          <div className="rounded-xl border border-gray-200 p-3">
            <div className="flex items-center gap-2 mb-2">
              <ShieldCheck className="w-4 h-4 text-blue-600" />
              <p className="text-sm font-semibold text-gray-900">Inspection checklist</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {visit.checklist.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => officerMode && visit.status === 'SCHEDULED' && onChecklistToggle?.(visit, item.id)}
                  disabled={!officerMode || visit.status !== 'SCHEDULED'}
                  className="flex w-full items-start gap-2 text-left text-sm text-gray-700 disabled:cursor-default"
                >
                  {item.completed ? <CheckCircle2 className="w-4 h-4 text-teal-600 mt-0.5" /> : <span className="mt-1 h-2 w-2 rounded-full bg-gray-300" />}
                  <span className={item.completed ? 'line-through text-gray-500' : ''}>{item.label}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {visit.coordination_note && (
          <div className="rounded-xl bg-blue-50 border border-blue-100 p-3 text-sm text-blue-900">
            <div className="flex items-start gap-2">
              <Users className="w-4 h-4 mt-0.5" />
              <span>{visit.coordination_note}</span>
            </div>
          </div>
        )}

        {officerMode && visit.status === 'SCHEDULED' && onStatus && (
          <div className="space-y-3">
            {editing && setEditStart && setEditEnd && onSaveReschedule && onCancelReschedule && (
              <div className="rounded-xl border border-blue-100 bg-blue-50 p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-blue-900">Reschedule visit</p>
                <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <input type="datetime-local" value={editStart} onChange={(e) => setEditStart(e.target.value)} className="rounded-xl border border-gray-300 bg-white px-3 py-2 text-sm" />
                  <input type="datetime-local" value={editEnd} onChange={(e) => setEditEnd(e.target.value)} className="rounded-xl border border-gray-300 bg-white px-3 py-2 text-sm" />
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button size="sm" onClick={onSaveReschedule}>Save new time</Button>
                  <Button size="sm" variant="outline" onClick={onCancelReschedule}>Cancel</Button>
                </div>
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              {!editing && onReschedule && <Button size="sm" variant="outline" onClick={() => onReschedule(visit)}>Reschedule</Button>}
              <Button size="sm" variant="outline" onClick={() => onStatus(visit.id, 'COMPLETED')}>
                Mark completed
              </Button>
              <Button size="sm" variant="outline" onClick={() => onStatus(visit.id, 'NO_SHOW')}>
                Mark no-show
              </Button>
              <Button size="sm" variant="danger" onClick={() => onStatus(visit.id, 'CANCELLED')}>
                Cancel visit
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function InspectionPlanner() {
  const { t } = useLanguage()
  const user = getSessionUser()
  const officerMode = ['OFFICER', 'ADMIN'].includes((user?.role || '').toUpperCase())

  const visitsQuery = useInspections(officerMode ? {} : {})
  const suggestionsQuery = useInspectionCoordinationSuggestions(undefined, true)
  const officersQuery = useInspectionOfficers(officerMode)
  const schedule = useScheduleInspection()
  const update = useUpdateInspection()

  const suggestions = suggestionsQuery.data?.suggestions || []
  const visits: InspectionVisit[] = visitsQuery.data?.inspections || []
  const officers = officersQuery.data?.officers || []

  const [selectedSuggestion, setSelectedSuggestion] = useState<any>(null)
  const [start, setStart] = useState(() => localInputValue(new Date(Date.now() + 2 * 24 * 60 * 60 * 1000 + 10 * 60 * 60 * 1000)))
  const [end, setEnd] = useState(() => localInputValue(new Date(Date.now() + 2 * 24 * 60 * 60 * 1000 + 12 * 60 * 60 * 1000)))
  const [officerId, setOfficerId] = useState('')
  const [location, setLocation] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')
  const [editingVisitId, setEditingVisitId] = useState<string | null>(null)
  const [editStart, setEditStart] = useState('')
  const [editEnd, setEditEnd] = useState('')

  const upcomingVisits = useMemo(
    () => visits.filter((v) => v.status === 'SCHEDULED').sort((a, b) => new Date(a.scheduled_start).getTime() - new Date(b.scheduled_start).getTime()),
    [visits],
  )
  const coordinatedCount = visits.filter((v) => v.coordinated).length

  const chooseSuggestion = (suggestion: any) => {
    setSelectedSuggestion(suggestion)
    setLocation(suggestion.location || '')
    setNotes('Prototype common-site planning: coordinate operationally where appropriate.')
  }

  const submitSchedule = async () => {
    setError('')
    if (!selectedSuggestion?.approval_ids?.length) {
      setError('Choose a coordination opportunity first.')
      return
    }
    try {
      await schedule.mutateAsync({
        approval_ids: selectedSuggestion.approval_ids,
        scheduled_start: new Date(start).toISOString(),
        scheduled_end: new Date(end).toISOString(),
        assigned_officer_id: officerId || undefined,
        location: location || undefined,
        notes: notes || undefined,
      })
      setSelectedSuggestion(null)
      setNotes('')
      visitsQuery.refetch()
      suggestionsQuery.refetch()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Could not schedule inspection visit')
    }
  }

  const startReschedule = (visit: InspectionVisit) => {
    setEditingVisitId(visit.id)
    setEditStart(localInputValue(new Date(visit.scheduled_start)))
    setEditEnd(localInputValue(new Date(visit.scheduled_end)))
    setError('')
  }

  const saveReschedule = async () => {
    if (!editingVisitId) return
    setError('')
    try {
      await update.mutateAsync({
        inspectionId: editingVisitId,
        payload: {
          scheduled_start: new Date(editStart).toISOString(),
          scheduled_end: new Date(editEnd).toISOString(),
        },
      })
      setEditingVisitId(null)
      visitsQuery.refetch()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Could not reschedule inspection')
    }
  }

  const toggleChecklist = async (visit: InspectionVisit, itemId: string) => {
    setError('')
    try {
      const checklist = visit.checklist.map((item) => item.id === itemId ? { ...item, completed: !item.completed } : item)
      await update.mutateAsync({ inspectionId: visit.id, payload: { checklist } })
      visitsQuery.refetch()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Could not update inspection checklist')
    }
  }

  const handleStatus = async (visitId: string, status: string) => {
    setError('')
    try {
      await update.mutateAsync({ inspectionId: visitId, payload: { status } })
      visitsQuery.refetch()
      suggestionsQuery.refetch()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Could not update inspection')
    }
  }

  if (visitsQuery.isLoading || (officerMode && officersQuery.isLoading)) {
    return <div className="py-24 text-center text-gray-600">Loading inspection planner...</div>
  }

  if (visitsQuery.isError) {
    return (
      <Card>
        <CardContent className="py-16 text-center">
          <AlertCircle className="w-10 h-10 mx-auto text-red-500" />
          <p className="mt-4 font-medium text-gray-900">Inspection data unavailable</p>
          <p className="mt-1 text-sm text-gray-600">Please refresh the planner and try again.</p>
          <Button className="mt-4" onClick={() => visitsQuery.refetch()}><RefreshCw className="w-4 h-4 mr-2" />Refresh</Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-8">
      <PageHeader
        icon={CalendarDays}
        title={t('pg.inspTitle')}
        purpose={officerMode
          ? t('pg.inspOfficer')
          : t('pg.inspUser')}
        action={<><Badge variant="outline">Prototype scheduling</Badge><Badge variant="outline">No live government API required</Badge></>}
      />

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
        <Card><CardContent className="p-5"><p className="text-sm text-gray-500">Upcoming visits</p><p className="mt-1 text-3xl font-extrabold tracking-tight text-blue-600">{upcomingVisits.length}</p></CardContent></Card>
        <Card><CardContent className="p-5"><p className="text-sm text-gray-500">Coordinated visits</p><p className="mt-1 text-3xl font-extrabold tracking-tight text-teal-600">{coordinatedCount}</p></CardContent></Card>
        <Card><CardContent className="p-5"><p className="text-sm text-gray-500">Open coordination opportunities</p><p className="mt-1 text-3xl font-extrabold tracking-tight text-amber-600">{suggestions.length}</p></CardContent></Card>
      </div>

      {officerMode && suggestions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Users className="w-5 h-5 text-blue-600" />Common inspection opportunities</CardTitle>
            <p className="text-sm text-gray-600">These are operational suggestions based on the same project/location. They do not change statutory inspection requirements.</p>
          </CardHeader>
          <CardContent className="space-y-4">
            {suggestions.map((suggestion: any) => (
              <div key={suggestion.project_id} className="border border-gray-200 rounded-xl p-4">
                <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                  <div>
                    <p className="font-semibold text-gray-900">{suggestion.company_name}</p>
                    <p className="text-sm text-gray-600 mt-1">{suggestion.project_name} · {suggestion.location}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {suggestion.applications.map((application: any) => (
                        <Badge key={application.id} variant="outline">{application.name}</Badge>
                      ))}
                    </div>
                    <p className="mt-3 text-sm text-blue-800">{suggestion.reason}</p>
                    <p className="mt-1 text-xs text-gray-500">{suggestion.site_visits_avoided} separate site visit(s) may be avoided by coordination.</p>
                  </div>
                  <Button onClick={() => chooseSuggestion(suggestion)}>Plan common visit</Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {officerMode && selectedSuggestion && (
        <Card className="border-blue-200">
          <CardHeader>
            <CardTitle>Schedule coordinated site visit</CardTitle>
            <p className="text-sm text-gray-600">{selectedSuggestion.project_name} · {selectedSuggestion.approval_count} approvals</p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <label className="text-sm font-medium text-gray-700">Start<input type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2" /></label>
              <label className="text-sm font-medium text-gray-700">End<input type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2" /></label>
              <label className="text-sm font-medium text-gray-700">Assigned officer<select value={officerId} onChange={(e) => setOfficerId(e.target.value)} className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2"><option value="">Assign to me</option>{officers.map((o: any) => <option key={o.id} value={o.id}>{o.name} · {o.email}</option>)}</select></label>
              <label className="text-sm font-medium text-gray-700">Location<input value={location} onChange={(e) => setLocation(e.target.value)} className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2" /></label>
            </div>
            <label className="text-sm font-medium text-gray-700 block">Notes<textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2" placeholder="Operational notes for the visit" /></label>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <div className="flex flex-wrap gap-2">
              <Button onClick={submitSchedule} disabled={schedule.isPending}>{schedule.isPending ? 'Scheduling...' : 'Schedule visit'}</Button>
              <Button variant="outline" onClick={() => setSelectedSuggestion(null)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {error && !selectedSuggestion && <p className="text-sm text-red-600">{error}</p>}

      <section>
        <div className="flex items-center justify-between mb-4">
          <div><h2 className="text-xl font-semibold text-gray-900">Upcoming inspections</h2><p className="text-sm text-gray-600 mt-1">{officerMode ? 'Manage scheduled visits and update operational status.' : 'Your inspection schedule across projects.'}</p></div>
          {!officerMode && <Link href="/dashboard/applications" className="text-sm font-medium text-blue-600">View applications →</Link>}
        </div>
        {upcomingVisits.length === 0 ? (
          <Card><CardContent className="py-14 text-center"><CalendarDays className="w-10 h-10 mx-auto text-gray-300" /><p className="mt-4 font-medium text-gray-900">No inspections scheduled</p><p className="mt-1 text-sm text-gray-600">Scheduled visits will appear here automatically.</p></CardContent></Card>
        ) : (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">{upcomingVisits.map((visit) => (
            <VisitCard
              key={visit.id}
              visit={visit}
              officerMode={officerMode}
              onStatus={handleStatus}
              onReschedule={startReschedule}
              onChecklistToggle={toggleChecklist}
              editing={editingVisitId === visit.id}
              editStart={editStart}
              editEnd={editEnd}
              setEditStart={setEditStart}
              setEditEnd={setEditEnd}
              onSaveReschedule={saveReschedule}
              onCancelReschedule={() => setEditingVisitId(null)}
            />
          ))}</div>
        )}
      </section>

      {!officerMode && visits.filter((v) => v.status !== 'SCHEDULED').length > 0 && (
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Inspection history</h2>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">{visits.filter((v) => v.status !== 'SCHEDULED').map((visit) => <VisitCard key={visit.id} visit={visit} officerMode={false} />)}</div>
        </section>
      )}

      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        <strong>Prototype boundary:</strong> UdyogSetu schedules and coordinates operational visits in the prototype. Statutory inspection requirements, departmental authority and final decisions remain with the authorized authority.
      </div>
    </div>
  )
}
