'use client'

import React, { useEffect, useMemo, useState } from 'react'
import ReactFlow, {
  Background,
  Controls,
  Edge,
  Node,
  useEdgesState,
  useNodesState,
} from 'reactflow'
import 'reactflow/dist/style.css'
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock3,
  GitBranch,
  Layers3,
  LockKeyhole,
  PlayCircle,
  ShieldCheck,
  Zap,
} from 'lucide-react'
import { useApprovalGraph } from '@/hooks/useApi'
import type { ApprovalRoadmapResponse } from '@/types'

interface DependencyGraphProps {
  projectId: string
}

type RoadmapView = 'roadmap' | 'map'

const STATUS_META: Record<string, { label: string; dot: string; border: string; bg: string }> = {
  APPROVED: { label: 'Approved', dot: 'bg-emerald-500', border: 'border-emerald-200', bg: 'bg-emerald-50' },
  SUBMITTED: { label: 'Submitted', dot: 'bg-blue-500', border: 'border-blue-200', bg: 'bg-blue-50' },
  UNDER_REVIEW: { label: 'Under review', dot: 'bg-amber-500', border: 'border-amber-200', bg: 'bg-amber-50' },
  QUERY_RAISED: { label: 'Query raised', dot: 'bg-red-500', border: 'border-red-200', bg: 'bg-red-50' },
  INSPECTION: { label: 'Inspection', dot: 'bg-violet-500', border: 'border-violet-200', bg: 'bg-violet-50' },
  DRAFT: { label: 'Draft', dot: 'bg-slate-400', border: 'border-slate-200', bg: 'bg-slate-50' },
  NOT_STARTED: { label: 'Not started', dot: 'bg-slate-400', border: 'border-slate-200', bg: 'bg-slate-50' },
}

const EXECUTION_META: Record<string, { label: string; className: string }> = {
  READY: { label: 'Ready', className: 'bg-green-100 text-green-800' },
  BLOCKED: { label: 'Blocked', className: 'bg-slate-100 text-slate-700' },
  IN_PROGRESS: { label: 'In progress', className: 'bg-blue-100 text-blue-800' },
  COMPLETED: { label: 'Completed', className: 'bg-emerald-100 text-emerald-800' },
}

function statusMeta(status: string) {
  return STATUS_META[status] ?? STATUS_META.NOT_STARTED
}

function executionMeta(state: string) {
  return EXECUTION_META[state] ?? EXECUTION_META.READY
}

function formatDays(days: number) {
  return `${days} day${days === 1 ? '' : 's'}`
}

export function ApprovalDependencyGraph({ projectId }: DependencyGraphProps) {
  const { data: rawData, isLoading, isError } = useApprovalGraph(projectId)
  const data = rawData as ApprovalRoadmapResponse | undefined
  const [view, setView] = useState<RoadmapView>('roadmap')
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])

  const criticalIds = useMemo(() => new Set(data?.critical_path?.approval_ids ?? []), [data])

  useEffect(() => {
    if (!data) return

    const stages = data.parallel_groups ?? []
    const nextNodes: Node[] = [
      {
        id: 'project',
        data: { label: 'Project Initiated' },
        position: { x: 40, y: 40 },
        style: {
          background: '#2563eb',
          color: '#fff',
          border: '2px solid #1d4ed8',
          borderRadius: 12,
          padding: 12,
          fontWeight: 700,
          minWidth: 170,
          textAlign: 'center' as const,
        },
      },
    ]

    stages.forEach((stage) => {
      stage.approvals.forEach((approval, rowIndex) => {
        const level = stage.stage - 1
        const isCritical = criticalIds.has(approval.id)
        const meta = statusMeta(approval.status)
        nextNodes.push({
          id: approval.id,
          data: {
            label: (
              <div className="text-left">
                <div className="flex items-start justify-between gap-2">
                  <span className="font-semibold leading-tight">{approval.name}</span>
                  {isCritical && <span className="rounded-full bg-yellow-300 px-1.5 py-0.5 text-[9px] font-bold text-yellow-950">CRITICAL</span>}
                </div>
                <div className="mt-1 text-[11px] opacity-90">{approval.department}</div>
                <div className="mt-2 flex items-center justify-between gap-2 text-[10px] opacity-80">
                  <span>{formatDays(approval.days)}</span>
                  <span>{meta.label}</span>
                </div>
              </div>
            ),
          },
          position: {
            x: 290 + level * 280,
            y: 25 + rowIndex * 125,
          },
          style: {
            background: isCritical ? '#fff7cc' : '#ffffff',
            color: '#111827',
            border: isCritical ? '2px solid #eab308' : '2px solid #cbd5e1',
            boxShadow: isCritical ? '0 8px 18px rgba(202, 138, 4, 0.15)' : '0 4px 12px rgba(15, 23, 42, 0.06)',
            borderRadius: 12,
            padding: 12,
            width: 230,
          },
        })
      })
    })

    const nextEdges: Edge[] = []
    ;(data.edges ?? []).forEach((edge, index) => {
      const onCritical = criticalIds.has(edge.source) && criticalIds.has(edge.target)
      nextEdges.push({
        id: edge.id || `edge-${index}`,
        source: edge.source,
        target: edge.target,
        animated: onCritical,
        label: onCritical ? 'critical path' : undefined,
        style: onCritical
          ? { stroke: '#eab308', strokeWidth: 3 }
          : { stroke: '#94a3b8', strokeWidth: 1.5 },
        labelStyle: { fontSize: 10, fontWeight: 600 },
      })
    })

    const hasIncoming = new Set((data.edges ?? []).map((edge) => edge.target))
    ;(data.nodes ?? []).forEach((approval) => {
      if (!hasIncoming.has(approval.id)) {
        nextEdges.push({
          id: `project-${approval.id}`,
          source: 'project',
          target: approval.id,
          style: { stroke: '#cbd5e1', strokeWidth: 1.5 },
        })
      }
    })

    setNodes(nextNodes)
    setEdges(nextEdges)
  }, [data, criticalIds, setEdges, setNodes])

  if (isLoading) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white py-16 text-center text-gray-600">
        <GitBranch className="mx-auto h-8 w-8 text-blue-600" />
        <p className="mt-3 text-sm">Building your approval roadmap...</p>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-8 text-center">
        <AlertTriangle className="mx-auto h-8 w-8 text-red-600" />
        <p className="mt-3 font-medium text-red-900">We couldn't load the approval roadmap.</p>
        <p className="mt-1 text-sm text-red-700">Run the approval analysis again and reopen this page.</p>
      </div>
    )
  }

  const summary = data.summary
  const groups = data.parallel_groups ?? []
  const schedule = data.schedule ?? []
  const criticalNames = data.critical_path?.names ?? []
  const timelineDays = Math.max(summary.parallel_duration_days || 0, 1)

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-gradient-to-br from-white to-slate-50 p-5 sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-800">
                <Layers3 className="h-3.5 w-3.5" /> Approval roadmap
              </span>
              {summary.warning && <span className="text-xs text-slate-500">Estimated timeline</span>}
              {rawData?.__offlineCachedAt && <span className="text-xs font-medium text-amber-700">Offline checklist snapshot</span>}
            </div>
            <h3 className="mt-3 text-xl font-bold text-gray-900 sm:text-2xl">How your approvals move together</h3>
            <p className="mt-2 text-sm leading-6 text-gray-600">
              UDYOGSETU uses configured approval dependencies and processing durations to show which approvals can be prepared in parallel and which ones must wait for another approval.
            </p>
          </div>
          <div className="flex rounded-lg border border-gray-200 bg-white p-1">
            <button
              type="button"
              onClick={() => setView('roadmap')}
              className={`rounded-md px-3 py-2 text-sm font-medium ${view === 'roadmap' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-50'}`}
            >
              Roadmap
            </button>
            <button
              type="button"
              onClick={() => setView('map')}
              className={`rounded-md px-3 py-2 text-sm font-medium ${view === 'map' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-50'}`}
            >
              Dependency Map
            </button>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-5">
          <Metric label="Approvals" value={summary.total_count} icon={Layers3} />
          <Metric label="Mandatory" value={summary.mandatory_count} icon={ShieldCheck} />
          <Metric label="Parallel journey" value={formatDays(summary.parallel_duration_days)} icon={Clock3} />
          <Metric label="Sequential" value={formatDays(summary.sequential_duration_days)} icon={ArrowRight} />
          <Metric label="Theoretical saving" value={formatDays(summary.theoretical_time_saved_days)} icon={Zap} emphasis />
        </div>
      </div>

      {view === 'roadmap' ? (
        <>
          <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 sm:p-5">
            <div className="flex items-start gap-3">
              <div className="rounded-lg bg-blue-600 p-2 text-white">
                <Zap className="h-5 w-5" />
              </div>
              <div>
                <p className="font-semibold text-blue-950">Parallel processing insight</p>
                <p className="mt-1 text-sm leading-6 text-blue-900">
                  Treating independent approvals as parallel work gives an estimated journey of <strong>{formatDays(summary.parallel_duration_days)}</strong> instead of <strong>{formatDays(summary.sequential_duration_days)}</strong> if every approval were handled one after another.
                </p>
                <p className="mt-1 text-xs text-blue-700">This is a planning estimate, not a statutory processing guarantee.</p>
              </div>
            </div>
          </div>

          {criticalNames.length > 0 && (
            <div className="rounded-xl border border-yellow-200 bg-yellow-50 p-4 sm:p-5">
              <div className="flex items-start gap-3">
                <div className="rounded-lg bg-yellow-400 p-2 text-yellow-950">
                  <GitBranch className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <p className="font-semibold text-yellow-950">Critical path</p>
                  <p className="mt-1 text-sm text-yellow-900">
                    This chain currently drives the overall estimated journey: {criticalNames.join(' → ')}
                  </p>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-4">
            {groups.length === 0 ? (
              <div className="rounded-xl border border-gray-200 bg-white py-14 text-center text-gray-600">
                No applicable approvals have been generated for this project yet.
              </div>
            ) : (
              groups.map((group) => (
                <div key={group.stage} className="rounded-xl border border-gray-200 bg-white p-4 sm:p-5">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 text-sm font-bold text-slate-700">{group.stage}</span>
                        <h4 className="font-semibold text-gray-900">Approval stage {group.stage}</h4>
                      </div>
                      <p className="mt-1 pl-10 text-sm text-gray-500">
                        {group.can_run_in_parallel ? 'These approvals can be prepared in parallel because they have no unmet dependency between them.' : 'This stage contains a dependency chain that must be respected.'}
                      </p>
                    </div>
                    <span className={`inline-flex w-fit items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${group.can_run_in_parallel ? 'bg-green-100 text-green-800' : 'bg-slate-100 text-slate-700'}`}>
                      {group.can_run_in_parallel ? <Zap className="h-3.5 w-3.5" /> : <LockKeyhole className="h-3.5 w-3.5" />}
                      {group.can_run_in_parallel ? 'Parallel' : 'Dependency stage'}
                    </span>
                  </div>

                  <div className="mt-4 grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
                    {group.approvals.map((approval) => {
                      const node = data.nodes.find((item) => item.id === approval.id)
                      const status = statusMeta(approval.status)
                      const execution = executionMeta(node?.execution_state ?? 'READY')
                      const isCritical = criticalIds.has(approval.id)
                      return (
                        <div key={approval.id} className={`rounded-xl border p-4 ${isCritical ? 'border-yellow-300 bg-yellow-50/70' : 'border-gray-200 bg-gray-50/70'}`}>
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <p className="font-semibold text-gray-900">{approval.name}</p>
                              <p className="mt-0.5 text-xs text-gray-500">{approval.department}</p>
                            </div>
                            {isCritical && <span className="rounded-full bg-yellow-200 px-2 py-0.5 text-[10px] font-bold text-yellow-900">CRITICAL</span>}
                          </div>
                          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
                            <span className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-1 ${status.bg} ${status.border} text-gray-700`}>
                              <span className={`h-1.5 w-1.5 rounded-full ${status.dot}`} />
                              {status.label}
                            </span>
                            <span className={`rounded-full px-2 py-1 font-medium ${execution.className}`}>{execution.label}</span>
                            <span className="rounded-full bg-white px-2 py-1 text-gray-600">~{formatDays(approval.days)}</span>
                          </div>
                          {node && node.dependencies.length > 0 && (
                            <p className="mt-3 text-xs leading-5 text-gray-600">
                              <span className="font-medium text-gray-800">Waits for:</span> {node.dependencies.join(', ')}
                            </p>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              ))
            )}
          </div>

          {schedule.length > 0 && (
            <div className="rounded-xl border border-gray-200 bg-white p-4 sm:p-5">
              <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h4 className="font-semibold text-gray-900">Earliest-start timeline</h4>
                  <p className="mt-1 text-sm text-gray-500">Approvals are positioned from their earliest dependency-safe start. Bars may overlap when work can run in parallel.</p>
                </div>
                <span className="text-xs text-gray-500">0 → {formatDays(timelineDays)}</span>
              </div>
              <div className="mt-5 overflow-x-auto">
                <div className="min-w-[820px] space-y-2">
                  <div className="ml-[220px] grid grid-cols-4 text-[10px] text-gray-400">
                    {[0, 1, 2, 3].map((step) => (
                      <span key={step}>{formatDays(Math.round((timelineDays * step) / 3))}</span>
                    ))}
                  </div>
                  {schedule.map((item) => {
                    const left = (item.start_day / timelineDays) * 100
                    const width = Math.max((item.duration_days / timelineDays) * 100, 2)
                    return (
                      <div key={item.id} className="grid grid-cols-[210px_1fr] items-center gap-3">
                        <div className="truncate text-sm text-gray-700" title={item.name}>{item.name}</div>
                        <div className="relative h-9 rounded-lg bg-slate-100">
                          <div className="absolute inset-y-0 left-0 w-px bg-slate-300" />
                          <div
                            className={`absolute inset-y-1 flex items-center rounded-md px-2 text-[10px] font-semibold ${item.critical ? 'bg-yellow-400 text-yellow-950' : 'bg-blue-500 text-white'}`}
                            style={{ left: `${Math.min(left, 97)}%`, width: `${Math.max(Math.min(width, 100 - Math.min(left, 97)), 2)}%` }}
                            title={`${item.name}: day ${item.start_day}–${item.finish_day}`}
                          >
                            <span className="truncate">{item.duration_days}d</span>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )}

          {(data.warnings ?? []).length > 0 && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              <div className="flex items-start gap-2"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /> <div>{data.warnings.map((warning) => <p key={warning}>{warning}</p>)}</div></div>
            </div>
          )}
        </>
      ) : (
        <>
          <div className="rounded-xl border border-gray-200 bg-white p-3 text-xs text-gray-500">
            Each arrow represents a configured dependency. Yellow nodes and edges form the current critical path.
          </div>
          <div className="h-[620px] overflow-hidden rounded-xl border border-gray-200 bg-white">
            <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} fitView fitViewOptions={{ padding: 0.16 }} minZoom={0.4} maxZoom={1.4}>
              <Background gap={20} size={1} />
              <Controls />
            </ReactFlow>
          </div>
        </>
      )}

      <div className="grid gap-3 sm:grid-cols-3">
        <Legend icon={<Zap className="h-4 w-4" />} title="Parallel" text="Independent approvals can be worked together." />
        <Legend icon={<GitBranch className="h-4 w-4" />} title="Critical path" text="The chain currently driving the estimated journey." />
        <Legend icon={<CheckCircle2 className="h-4 w-4" />} title="Configured estimate" text="Durations come from the approval rules, not a government guarantee." />
      </div>
    </div>
  )
}

function Metric({ label, value, icon: Icon, emphasis = false }: { label: string; value: string | number; icon: React.ElementType; emphasis?: boolean }) {
  return (
    <div className={`rounded-xl border p-3 sm:p-4 ${emphasis ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-white'}`}>
      <Icon className={`h-4 w-4 ${emphasis ? 'text-green-700' : 'text-blue-600'}`} />
      <p className="mt-2 text-[11px] font-medium uppercase tracking-wide text-gray-500">{label}</p>
      <p className={`mt-1 text-lg font-bold sm:text-xl ${emphasis ? 'text-green-800' : 'text-gray-900'}`}>{value}</p>
    </div>
  )
}

function Legend({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <div className="flex items-center gap-2 font-semibold text-gray-900">{icon}<span>{title}</span></div>
      <p className="mt-1 text-xs leading-5 text-gray-500">{text}</p>
    </div>
  )
}

export default ApprovalDependencyGraph
