'use client'

import Link from 'next/link'
import { CalendarDays, Clock3, MapPin, Users } from 'lucide-react'
import { useApplicationInspections } from '@/hooks/useApi'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

function formatDateTime(value: string) {
  return new Date(value).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
}

export default function InspectionApplicationPanel({ applicationId }: { applicationId: string }) {
  const { data, isLoading } = useApplicationInspections(applicationId)
  const visits = data?.inspections || []

  if (isLoading) {
    return <Card><CardContent className="py-8 text-sm text-gray-500">Loading inspection schedule...</CardContent></Card>
  }

  if (visits.length === 0) return null

  const active = visits.find((visit: any) => visit.status === 'SCHEDULED') || visits[0]

  return (
    <Card className="border-blue-200">
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="flex items-center gap-2"><CalendarDays className="w-5 h-5 text-blue-600" />Inspection schedule</CardTitle>
          <Badge variant={active.status === 'COMPLETED' ? 'success' : active.status === 'CANCELLED' ? 'danger' : 'info'}>{active.status.replace('_', ' ')}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
          <div className="flex gap-2 items-start"><CalendarDays className="w-4 h-4 mt-0.5 text-blue-600" /><span>{formatDateTime(active.scheduled_start)}</span></div>
          <div className="flex gap-2 items-start"><Clock3 className="w-4 h-4 mt-0.5 text-blue-600" /><span>Ends {formatDateTime(active.scheduled_end)}</span></div>
          <div className="flex gap-2 items-start sm:col-span-2"><MapPin className="w-4 h-4 mt-0.5 text-blue-600" /><span>{active.location || 'Location to be confirmed'}</span></div>
        </div>
        {active.assigned_officer_name && <p className="text-sm text-gray-600">Assigned officer: <span className="font-medium text-gray-900">{active.assigned_officer_name}</span></p>}
        {active.coordinated && <div className="rounded-xl bg-blue-50 border border-blue-100 p-3 text-sm text-blue-900 flex gap-2"><Users className="w-4 h-4 mt-0.5" /><span>This is a coordinated site visit covering {active.approvals.length} application(s).</span></div>}
        <Link href="/dashboard/inspections" className="inline-flex text-sm font-medium text-blue-600">Open inspection planner →</Link>
      </CardContent>
    </Card>
  )
}
