'use client'

import Link from 'next/link'
import { ArrowRight, CheckCircle2, CircleAlert, FlaskConical, Info, Loader2, RefreshCw, ShieldCheck } from 'lucide-react'
import { useDemoReadiness } from '@/hooks/useApi'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const entrepreneurSteps = [
  { label: 'Business Profile', path: '/dashboard/profile' },
  { label: 'Unified Command Center', path: null },
  { label: 'Approval Roadmap', suffix: '/approvals' },
  { label: 'Application Preparation', path: null, key: 'preparation' },
  { label: 'Pre-Submission Readiness', suffix: '/approvals' },
  { label: 'Query Resolution', path: null, key: 'query' },
  { label: 'Inspection Planner', path: '/dashboard/inspections' },
  { label: 'Grievance Workflow', path: '/dashboard/grievances' },
  { label: 'Notifications', path: '/dashboard/notifications' },
  { label: 'Regulatory Updates', path: '/dashboard/regulatory' },
  { label: 'Scenario Simulator', path: null },
  { label: 'Government Integrations', path: '/dashboard/integrations' },
]

export default function DemoCenterPage() {
  const { data, isLoading, isError, refetch, isFetching } = useDemoReadiness()
  const projectId = data?.project_id as string | undefined

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800 ring-1 ring-inset ring-amber-200">
            <FlaskConical className="h-4 w-4" />
            SIH prototype demo mode
          </div>
          <h1 className="mt-3 text-3xl font-bold text-gray-900">SIH Demo Center</h1>
          <p className="mt-1 max-w-3xl text-gray-600">Verify the seeded walkthrough before presenting UDYOGSETU. Every check is read-only and uses prototype data; nothing here represents a live government transaction.</p>
        </div>
        <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
          Recheck demo
        </Button>
      </div>

      {isLoading ? (
        <Card><CardContent className="flex items-center justify-center py-20 text-gray-600"><Loader2 className="mr-2 h-5 w-5 animate-spin" />Checking demo readiness...</CardContent></Card>
      ) : isError ? (
        <Card className="border-red-200"><CardContent className="py-16 text-center"><p className="font-medium text-red-900">Demo readiness is unavailable.</p><p className="mt-1 text-sm text-red-700">Make sure the backend is running and the demo database is accessible.</p><Button className="mt-4" variant="outline" onClick={() => refetch()}>Retry</Button></CardContent></Card>
      ) : (
        <>
          <div className={`rounded-2xl border p-6 ${data?.ready ? 'border-green-200 bg-green-50' : 'border-amber-200 bg-amber-50'}`}>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-gray-600">Demo readiness</p>
                <p className="mt-1 text-4xl font-bold text-gray-900">{data?.score ?? 0}%</p>
                <p className="mt-1 text-sm text-gray-700">{data?.passed ?? 0} of {data?.total ?? 0} checks passing</p>
              </div>
              <Badge variant={data?.ready ? 'success' : 'warning'} className="w-fit">{data?.ready ? 'READY TO PRESENT' : 'ACTION REQUIRED'}</Badge>
            </div>
          </div>

          {data?.disclaimer && <Card className="border-blue-200 bg-blue-50/70"><CardContent className="p-5 text-sm leading-6 text-blue-900"><div className="flex gap-3"><Info className="mt-0.5 h-5 w-5 shrink-0" /><span>{data.disclaimer}</span></div></CardContent></Card>}

          <div className="grid gap-5 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>Pre-flight checks</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {(data?.checks || []).map((check: any) => (
                  <div key={check.key} className="flex items-start gap-3 rounded-xl border border-gray-200 p-4">
                    {check.ok ? <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-green-600" /> : <CircleAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />}
                    <div className="min-w-0 flex-1"><p className="font-medium text-gray-900">{check.label}</p><p className="mt-1 text-sm text-gray-600">{check.detail}</p></div>
                    <Link href={check.href} className="shrink-0 text-sm font-medium text-blue-700 hover:underline">Open</Link>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Suggested presenter flow</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {entrepreneurSteps.map((step, index) => {
                  const href = step.path
                    || (step.key === 'query' && data?.query_application_id ? `/dashboard/applications/${data.query_application_id}/query` : null)
                    || (step.key === 'preparation' && data?.preparation_application_id ? `/dashboard/applications/${data.preparation_application_id}/prepare` : null)
                    || (step.suffix && projectId ? `/dashboard/${projectId}${step.suffix}` : projectId ? `/dashboard/${projectId}` : '/dashboard')
                  return (
                    <Link key={step.label} href={href} className="group flex items-center gap-3 rounded-xl border border-gray-200 p-4 transition hover:border-blue-200 hover:bg-blue-50/40">
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-50 text-sm font-bold text-blue-700">{index + 1}</span>
                      <span className="flex-1 font-medium text-gray-900">{step.label}</span>
                      <ArrowRight className="h-4 w-4 text-gray-400 transition group-hover:translate-x-0.5 group-hover:text-blue-600" />
                    </Link>
                  )
                })}
                <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                  <div className="flex gap-3"><ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-slate-600" /><p><strong>Presenter tip:</strong> start with the project Command Center, then demonstrate one query, one inspection, one grievance and one scenario. The Demo Center is your pre-flight checklist, not a separate product workflow.</p></div>
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
