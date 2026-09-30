'use client'

import AuroraBackground from '@/components/fx/AuroraBackground'
import { useEffect, useMemo, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Beaker,
  Building2,
  CheckCircle2,
  ChevronRight,
  FileText,
  FlaskConical,
  Gift,
  Info,
  MapPin,
  Minus,
  ShieldAlert,
  Sparkles,
  TrendingUp,
} from 'lucide-react'
import { useProject, useScenarioCatalog, useSimulateProjectScenario } from '@/hooks/useApi'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import type { ScenarioCatalogItem, ScenarioSimulationResponse } from '@/types'

const FALLBACK_SCENARIOS: ScenarioCatalogItem[] = [
  { type: 'location_change', label: 'Change project location', description: 'Model location-specific planning signals and configured rule impact.', parameters: ['new_state', 'new_district', 'new_city'] },
  { type: 'sector_upgrade', label: 'Change sector / industry', description: 'See how a sector shift affects approvals and support schemes.', parameters: ['new_sector', 'new_industry'] },
  { type: 'investment_change', label: 'Change investment', description: 'Model approval and incentive catalogue changes from a different investment size.', parameters: ['new_investment_amount'] },
  { type: 'capacity_expansion', label: 'Increase production capacity', description: 'Model capacity-driven planning impacts using your scenario assumptions.', parameters: ['current_capacity', 'new_capacity'] },
  { type: 'boiler_addition', label: 'Add or remove boiler', description: 'See the approval and document effects of a boiler configuration change.', parameters: ['has_boiler'] },
  { type: 'hazardous_materials', label: 'Add or remove hazardous materials', description: 'Model the configured safety/environmental approval signals.', parameters: ['hazardous_materials'] },
  { type: 'timeline_compression', label: 'Compress target timeline', description: 'Test a shorter target against the current configured critical path.', parameters: ['target_days'] },
]

function formatCurrency(value?: number | null) {
  if (value === null || value === undefined) return '—'
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(value)
}

function deltaClass(value: number) {
  if (value > 0) return 'text-amber-700'
  if (value < 0) return 'text-teal-700'
  return 'text-slate-500'
}

function Delta({ value, suffix = '' }: { value: number; suffix?: string }) {
  if (value === 0) return <span className="inline-flex items-center gap-1 text-slate-500"><Minus className="h-3.5 w-3.5" />0{suffix}</span>
  const positive = value > 0
  return (
    <span className={`inline-flex items-center gap-1 font-semibold ${deltaClass(value)}`}>
      {positive ? <ArrowUpRight className="h-3.5 w-3.5" /> : <ArrowDownRight className="h-3.5 w-3.5" />}
      {positive ? '+' : ''}{value}{suffix}
    </span>
  )
}

function scenarioIcon(type: string) {
  switch (type) {
    case 'location_change': return MapPin
    case 'sector_upgrade': return Building2
    case 'investment_change': return TrendingUp
    case 'capacity_expansion': return FlaskConical
    case 'boiler_addition': return Beaker
    case 'hazardous_materials': return ShieldAlert
    case 'timeline_compression': return Sparkles
    default: return FlaskConical
  }
}

export default function ScenarioSimulator() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.projectId as string
  const { data: project, isLoading: projectLoading } = useProject(projectId)
  const { data: catalogData } = useScenarioCatalog()
  const simulate = useSimulateProjectScenario()
  const scenarios = (catalogData?.scenarios as ScenarioCatalogItem[] | undefined) || FALLBACK_SCENARIOS

  const [scenarioType, setScenarioType] = useState(scenarios[0]?.type || 'location_change')
  const [values, setValues] = useState<Record<string, string>>({
    new_state: '',
    new_district: '',
    new_city: '',
    new_sector: '',
    new_industry: '',
    new_investment_amount: project?.investment_amount ? String(project.investment_amount) : '',
    current_capacity: '100',
    new_capacity: '150',
    has_boiler: project?.has_boiler ? 'true' : 'false',
    hazardous_materials: project?.hazardous_materials ? 'true' : 'false',
    target_days: '30',
  })
  const [result, setResult] = useState<ScenarioSimulationResponse | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!project) return
    setValues((current) => ({
      ...current,
      new_investment_amount: project.investment_amount ? String(project.investment_amount) : current.new_investment_amount,
      has_boiler: project.has_boiler ? 'true' : 'false',
      hazardous_materials: project.hazardous_materials ? 'true' : 'false',
    }))
  }, [project])

  const selectedScenario = useMemo(
    () => scenarios.find((item) => item.type === scenarioType) || scenarios[0],
    [scenarioType, scenarios],
  )

  const setValue = (key: string, value: string) => setValues((current) => ({ ...current, [key]: value }))

  const run = async () => {
    setError('')
    setResult(null)
    const parameters: Record<string, any> = {}
    ;(selectedScenario?.parameters || []).forEach((key) => {
      const raw = values[key]
      if (key === 'new_investment_amount' || key === 'current_capacity' || key === 'new_capacity' || key === 'target_days') {
        parameters[key] = raw === '' ? null : Number(raw)
      } else if (key === 'has_boiler' || key === 'hazardous_materials') {
        parameters[key] = raw === 'true'
      } else {
        parameters[key] = raw
      }
    })

    try {
      const response = await simulate.mutateAsync({ projectId, scenarioType, parameters })
      setResult(response as ScenarioSimulationResponse)
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Could not run the scenario simulation.')
    }
  }

  if (projectLoading) return <div className="py-24 text-center text-slate-600">Loading project…</div>
  if (!project) return <div className="py-24 text-center text-slate-600">Project not found.</div>

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => router.push(`/dashboard/${projectId}`)}>
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to Command Center
        </Button>
      </div>

      <section className="relative isolate overflow-hidden rounded-3xl bg-navy p-6 text-cream shadow-soft sm:p-8">
        <div className="absolute inset-0 -z-10 opacity-[.10] bg-grid invert" aria-hidden="true" />
        <AuroraBackground className="-z-10 opacity-40" />
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="default">Scenario Simulator</Badge>
              <Badge variant="outline">Advisory planning</Badge>
            </div>
            <h1 className="mt-3 text-2xl font-extrabold tracking-tight text-cream sm:text-4xl">What happens if your project changes?</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-blue-100">
              Test location, sector, investment, capacity, safety and timeline scenarios before making a real project decision.
              UdyogSetu compares the current project against a read-only projected configuration.
            </p>
            <p className="mt-2 text-xs text-blue-200">Project: {project.name} · {project.company_name}</p>
          </div>
          <div className="rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-sm backdrop-blur">
            <p className="text-xs font-extrabold uppercase tracking-[.16em] text-blue-200">Current profile</p>
            <p className="mt-1 font-bold text-cream">{project.location_state || '—'} · {project.sector || '—'}</p>
            <p className="mt-1 text-xs text-blue-200">₹{formatCurrency(project.investment_amount)} investment · {project.location_district || '—'}</p>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[340px_minmax(0,1fr)]">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle>Choose a scenario</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {scenarios.map((scenario) => {
              const Icon = scenarioIcon(scenario.type)
              const active = scenario.type === scenarioType
              return (
                <button
                  key={scenario.type}
                  type="button"
                  onClick={() => { setScenarioType(scenario.type); setResult(null); setError('') }}
                  className={`w-full rounded-xl border p-3 text-left transition ${active ? 'border-blue-300 bg-blue-50 ring-1 ring-blue-200' : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'}`}
                >
                  <div className="flex items-start gap-3">
                    <div className={`mt-0.5 rounded-xl p-2 ${active ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600'}`}><Icon className="h-4 w-4" /></div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-slate-950">{scenario.label}</p>
                      <p className="mt-1 text-xs leading-5 text-slate-500">{scenario.description}</p>
                    </div>
                    {active && <ChevronRight className="mt-1 h-4 w-4 text-blue-600" />}
                  </div>
                </button>
              )
            })}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle>{selectedScenario?.label}</CardTitle>
                <p className="mt-1 text-xs text-slate-500">Only the scenario assumptions change. Your real project data is not modified.</p>
              </div>
              <Badge variant="outline">Read-only simulation</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {scenarioType === 'location_change' && (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <div><label className="text-sm font-medium text-slate-700">New state</label><Input className="mt-1" value={values.new_state} onChange={(e) => setValue('new_state', e.target.value)} placeholder="e.g. Gujarat" /></div>
                <div><label className="text-sm font-medium text-slate-700">New district</label><Input className="mt-1" value={values.new_district} onChange={(e) => setValue('new_district', e.target.value)} placeholder="e.g. Ahmedabad" /></div>
                <div><label className="text-sm font-medium text-slate-700">New city</label><Input className="mt-1" value={values.new_city} onChange={(e) => setValue('new_city', e.target.value)} placeholder="e.g. Ahmedabad" /></div>
              </div>
            )}

            {scenarioType === 'sector_upgrade' && (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div><label className="text-sm font-medium text-slate-700">New sector</label><Input className="mt-1" value={values.new_sector} onChange={(e) => setValue('new_sector', e.target.value)} placeholder="e.g. Chemicals" /></div>
                <div><label className="text-sm font-medium text-slate-700">New industry <span className="font-normal text-slate-400">(optional)</span></label><Input className="mt-1" value={values.new_industry} onChange={(e) => setValue('new_industry', e.target.value)} placeholder="Defaults to new sector" /></div>
              </div>
            )}

            {scenarioType === 'investment_change' && (
              <div className="max-w-md"><label className="text-sm font-medium text-slate-700">New investment amount (₹)</label><Input className="mt-1" type="number" min="0" value={values.new_investment_amount} onChange={(e) => setValue('new_investment_amount', e.target.value)} /></div>
            )}

            {scenarioType === 'capacity_expansion' && (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div><label className="text-sm font-medium text-slate-700">Current capacity</label><Input className="mt-1" type="number" min="0.000001" value={values.current_capacity} onChange={(e) => setValue('current_capacity', e.target.value)} /><p className="mt-1 text-xs text-slate-500">Use your own planning unit.</p></div>
                <div><label className="text-sm font-medium text-slate-700">New capacity</label><Input className="mt-1" type="number" min="0.000001" value={values.new_capacity} onChange={(e) => setValue('new_capacity', e.target.value)} /></div>
              </div>
            )}

            {(scenarioType === 'boiler_addition' || scenarioType === 'hazardous_materials') && (
              <div className="max-w-md">
                <label className="text-sm font-medium text-slate-700">Projected configuration</label>
                <Select className="mt-1" value={values[scenarioType === 'boiler_addition' ? 'has_boiler' : 'hazardous_materials']} onChange={(e) => setValue(scenarioType === 'boiler_addition' ? 'has_boiler' : 'hazardous_materials', e.target.value)}>
                  <option value="false">No</option>
                  <option value="true">Yes</option>
                </Select>
              </div>
            )}

            {scenarioType === 'timeline_compression' && (
              <div className="max-w-md"><label className="text-sm font-medium text-slate-700">Target timeline (days)</label><Input className="mt-1" type="number" min="0" value={values.target_days} onChange={(e) => setValue('target_days', e.target.value)} /><p className="mt-1 text-xs text-slate-500">Compared with the current configured critical-path estimate.</p></div>
            )}

            {error && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>}

            <div className="flex flex-wrap items-center gap-3 border-t border-slate-100 pt-5">
              <Button onClick={run} disabled={simulate.isPending}>
                {simulate.isPending ? 'Running scenario…' : 'Run scenario'}
                {!simulate.isPending && <ArrowRight className="ml-2 h-4 w-4" />}
              </Button>
              <div className="inline-flex items-center gap-2 text-xs text-slate-500"><Info className="h-3.5 w-3.5" /> No project data is changed by this action.</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {result && (
        <div className="space-y-6">
          <section className="grid grid-cols-2 gap-4 lg:grid-cols-6">
            <Metric label="Approvals" before={result.baseline.approval_count} after={result.projected.approval_count} />
            <Metric label="Required docs" before={result.baseline.required_document_count} after={result.projected.required_document_count} />
            <Metric label="Critical path" before={result.baseline.timeline.parallel_duration_days} after={result.projected.timeline.parallel_duration_days} suffix="d" />
            <Metric label="High-risk approvals" before={result.baseline.high_risk_approval_count} after={result.projected.high_risk_approval_count} />
            <Metric label="Parallel saving" before={result.baseline.timeline.theoretical_time_saved_days} after={result.projected.timeline.theoretical_time_saved_days} suffix="d" />
            <Metric label="Incentive matches" before={result.baseline.incentives.length} after={result.projected.incentives.length} />
          </section>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader><CardTitle>What changed?</CardTitle></CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <DeltaList title="Approvals added" items={result.changes.approvals_added} variant="add" empty="No new configured approvals." />
                  <DeltaList title="Approvals removed" items={result.changes.approvals_removed} variant="remove" empty="No configured approvals removed." />
                </div>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <SimpleList title="New required documents" items={result.changes.required_documents_added} icon={FileText} empty="No additional document types." />
                  <SimpleList title="Incentives newly matched" items={result.changes.new_incentives.map((item) => item.name)} icon={Gift} empty="No newly matched incentive catalogue items." />
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                    <div><p className="text-xs text-slate-500">Critical path change</p><p className="mt-1 text-lg font-bold text-slate-950"><Delta value={result.changes.timeline_delta_days} suffix=" days" /></p></div>
                    <div><p className="text-xs text-slate-500">High-risk change</p><p className="mt-1 text-lg font-bold text-slate-950"><Delta value={result.changes.high_risk_approval_delta} suffix=" approvals" /></p></div>
                    <div><p className="text-xs text-slate-500">Risk signal</p><p className="mt-1"><Badge variant={result.changes.risk_change === 'INCREASED' ? 'warning' : result.changes.risk_change === 'DECREASED' ? 'success' : 'outline'}>{result.changes.risk_change}</Badge></p></div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Scenario guidance</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {result.recommendations.map((recommendation, index) => (
                  <div key={index} className="flex gap-3 rounded-xl border border-slate-200 bg-white p-3">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-blue-600" />
                    <p className="text-sm leading-5 text-slate-700">{recommendation}</p>
                  </div>
                ))}
                {result.changes.risk_indicators.map((indicator, index) => (
                  <div key={`risk-${index}`} className="flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-3">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
                    <p className="text-sm leading-5 text-amber-900">{indicator}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader><CardTitle>Approval timeline comparison</CardTitle></CardHeader>
            <CardContent>
              <TimelineComparison result={result} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Projected incentive impact</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {[...result.projected.incentives].slice(0, 6).map((scheme) => {
                  const previous = result.baseline.incentives.find((item) => item.id === scheme.id)
                  return (
                    <div key={scheme.id} className="rounded-xl border border-slate-200 p-4">
                      <div className="flex items-start justify-between gap-3"><div><p className="font-semibold text-slate-950">{scheme.name}</p><p className="mt-1 text-xs text-slate-500">Catalogue match signal</p></div><Badge variant={scheme.match_score >= 80 ? 'success' : 'outline'}>{scheme.match_score}</Badge></div>
                      <p className="mt-3 text-sm text-slate-600">{scheme.match_reason || 'Projected catalogue match.'}</p>
                      {previous && scheme.match_score !== previous.match_score && <p className="mt-2 text-xs font-medium text-slate-600">Score change: <Delta value={scheme.match_score - previous.match_score} /></p>}
                    </div>
                  )
                })}
                {result.projected.incentives.length === 0 && <p className="text-sm text-slate-600">No incentive matches were returned under the projected catalogue rules.</p>}
              </div>
            </CardContent>
          </Card>

          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
            <div className="flex gap-3"><AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" /><div><p className="font-semibold text-amber-950">Planning-only result</p><ul className="mt-2 space-y-1 text-sm leading-5 text-amber-900">{result.warnings.map((warning, index) => <li key={index}>• {warning}</li>)}</ul></div></div>
          </div>
        </div>
      )}
    </div>
  )
}

function Metric({ label, before, after, suffix = '' }: { label: string; before: number; after: number; suffix?: string }) {
  return (
    <Card><CardContent className="p-4"><p className="text-xs text-slate-500">{label}</p><p className="mt-1 text-2xl font-bold text-slate-950">{after}{suffix}</p><p className="mt-1 text-xs text-slate-500">Baseline {before}{suffix} · <Delta value={after - before} suffix={suffix} /></p></CardContent></Card>
  )
}

function DeltaList({ title, items, variant, empty }: { title: string; items: ScenarioSimulationResponse['changes']['approvals_added']; variant: 'add' | 'remove'; empty: string }) {
  return (
    <div><div className="mb-2 flex items-center gap-2"><p className="text-sm font-semibold text-slate-950">{title}</p><Badge variant={variant === 'add' ? 'success' : 'outline'}>{items.length}</Badge></div>{items.length ? <div className="space-y-2">{items.map((item) => <div key={item.name} className="rounded-xl border border-slate-200 p-3"><div className="flex items-start justify-between gap-2"><p className="text-sm font-medium text-slate-900">{item.name}</p><span className="text-xs text-slate-500">{item.estimated_processing_days}d</span></div><p className="mt-1 text-xs text-slate-500">{item.department} · {item.risk_level || 'MEDIUM'} risk</p></div>)}</div> : <p className="rounded-xl border border-dashed border-slate-200 p-4 text-xs text-slate-500">{empty}</p>}</div>
  )
}

function SimpleList({ title, items, icon: Icon, empty }: { title: string; items: string[]; icon: any; empty: string }) {
  return <div><div className="mb-2 flex items-center gap-2"><p className="text-sm font-semibold text-slate-950">{title}</p><Badge variant="outline">{items.length}</Badge></div>{items.length ? <div className="space-y-2">{items.map((item) => <div key={item} className="flex items-center gap-2 rounded-xl border border-slate-200 p-3"><Icon className="h-4 w-4 text-slate-500" /><span className="text-sm text-slate-700">{item}</span></div>)}</div> : <p className="rounded-xl border border-dashed border-slate-200 p-4 text-xs text-slate-500">{empty}</p>}</div>
}

function TimelineComparison({ result }: { result: ScenarioSimulationResponse }) {
  const rows = result.roadmap.projected.schedule.slice(0, 12)
  const maxDay = Math.max(result.projected.timeline.parallel_duration_days, 1)
  return <div className="space-y-2">{rows.map((item: any) => <div key={item.id} className="grid grid-cols-[150px_minmax(0,1fr)_70px] items-center gap-3 text-xs"><div className="truncate font-medium text-slate-800">{item.name}</div><div className="relative h-7 rounded-lg bg-slate-100"><div className={`absolute top-1 h-5 rounded ${item.critical ? 'bg-blue-600' : 'bg-slate-300'}`} style={{ left: `${(item.start_day / maxDay) * 100}%`, width: `${Math.max(((item.finish_day - item.start_day) / maxDay) * 100, 2)}%` }} title={`${item.start_day}–${item.finish_day} days`} /></div><div className="text-right text-slate-500">{item.duration_days}d</div></div>)}</div>
}
