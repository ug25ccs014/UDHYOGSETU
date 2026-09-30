'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import {
  AlertTriangle,
  ArrowRight,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ExternalLink,
  FileText,
  Filter,
  History,
  Info,
  Loader2,
  RefreshCw,
  Search,
  Sparkles,
  X,
} from 'lucide-react'
import { useProjects, useProjectRegulatoryChanges, useRecentRegulatoryChanges, useRegulatoryChange } from '@/hooks/useApi'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select } from '@/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { RegulatoryChangeDetail, RegulatoryChangeItem } from '@/types'

interface RegulatoryChangeCenterProps {
  projectId?: string
}

const statusVariant: Record<string, 'success' | 'warning' | 'danger' | 'outline'> = {
  ACTIVE: 'success',
  UPCOMING: 'warning',
  EXPIRED: 'danger',
  UNKNOWN: 'outline',
}

const changeVariant: Record<string, 'success' | 'danger' | 'warning' | 'outline'> = {
  ADDED: 'success',
  REMOVED: 'danger',
  MODIFIED: 'warning',
}

function formatDate(value?: string | null) {
  if (!value) return 'Not specified'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Not specified' : date.toLocaleDateString()
}

function ChangeCard({
  change,
  selected,
  onSelect,
}: {
  change: RegulatoryChangeItem
  selected: boolean
  onSelect: () => void
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full text-left rounded-xl border p-5 transition ${selected ? 'border-blue-400 bg-blue-50/40 shadow-sm' : 'border-gray-200 bg-white hover:border-blue-300 hover:shadow-sm'}`}
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-semibold text-gray-900">{change.title}</h3>
            <Badge variant={statusVariant[change.effective_status] || 'outline'}>
              {change.effective_status}
            </Badge>
            {change.impact.potentially_affected && (
              <Badge variant="warning">Potential impact</Badge>
            )}
          </div>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
            <span>{change.department || 'Unassigned department'}</span>
            <span>Version {change.version}</span>
            {change.previous_version && <span>Previous {change.previous_version}</span>}
            <span>Effective {formatDate(change.effective_date)}</span>
          </div>
        </div>
        <ChevronDown className={`h-5 w-5 shrink-0 text-gray-400 transition ${selected ? 'rotate-180 text-blue-500' : ''}`} />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
        <div className="rounded-xl bg-gray-50 p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-500">What changed</p>
          <p className="mt-1 text-sm font-medium text-gray-900">{change.text_change_summary}</p>
        </div>
        <div className="rounded-xl bg-gray-50 p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Potentially affected</p>
          <p className="mt-1 text-sm font-medium text-gray-900">
            {change.impact.approval_count} approvals · {change.impact.project_count} projects
          </p>
        </div>
        <div className="rounded-xl bg-gray-50 p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Field changes</p>
          <p className="mt-1 text-sm font-medium text-gray-900">{change.changed_field_count}</p>
        </div>
      </div>
    </button>
  )
}

function DetailPanel({ detail, onClose }: { detail: RegulatoryChangeDetail; onClose: () => void }) {
  return (
    <Card className="border-blue-200 shadow-sm">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle>{detail.title}</CardTitle>
            <Badge variant={statusVariant[detail.effective_status] || 'outline'}>{detail.effective_status}</Badge>
          </div>
          <p className="mt-1 text-sm text-gray-600">
            Version {detail.version}{detail.supersedes_version ? ` · supersedes ${detail.supersedes_version}` : ''}
          </p>
        </div>
        <Button size="sm" variant="ghost" onClick={onClose} aria-label="Close details">
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <div className="flex items-start gap-2">
            <Info className="mt-0.5 h-4 w-4 shrink-0" />
            <p>{detail.note}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <div>
            <p className="text-xs text-gray-500">Department</p>
            <p className="mt-1 text-sm font-medium text-gray-900">{detail.department || '—'}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Effective date</p>
            <p className="mt-1 text-sm font-medium text-gray-900">{formatDate(detail.effective_date)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Similarity</p>
            <p className="mt-1 text-sm font-medium text-gray-900">{Math.round(detail.similarity * 100)}%</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Potential projects</p>
            <p className="mt-1 text-sm font-medium text-gray-900">{detail.impact.project_count}</p>
          </div>
        </div>

        {detail.change_items.length > 0 && (
          <div>
            <h4 className="font-semibold text-gray-900">Change breakdown</h4>
            <div className="mt-3 space-y-3">
              {detail.change_items.map((item, index) => (
                <div key={`${item.section}-${index}`} className="rounded-xl border border-gray-200 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={changeVariant[item.type] || 'outline'}>{item.type}</Badge>
                    <span className="text-sm font-medium text-gray-900">{item.section}</span>
                  </div>
                  {item.type === 'MODIFIED' ? (
                    <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                      <div className="rounded-lg bg-red-50 p-3">
                        <p className="text-xs font-semibold uppercase tracking-wide text-red-700">Previous</p>
                        <p className="mt-1 text-sm leading-6 text-red-950">{item.old_text || '—'}</p>
                      </div>
                      <div className="rounded-lg bg-teal-50 p-3">
                        <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">Current</p>
                        <p className="mt-1 text-sm leading-6 text-teal-600">{item.new_text || '—'}</p>
                      </div>
                    </div>
                  ) : (
                    <p className="mt-2 text-sm leading-6 text-gray-700">{item.new_text || item.old_text || '—'}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {detail.changed_fields.length > 0 && (
          <div>
            <h4 className="font-semibold text-gray-900">Metadata changes</h4>
            <div className="mt-3 overflow-hidden rounded-xl border border-gray-200">
              {detail.changed_fields.map((field) => (
                <div key={field.field} className="grid grid-cols-[120px_1fr] gap-4 border-b border-gray-100 px-4 py-3 text-sm last:border-b-0">
                  <span className="font-medium capitalize text-gray-600">{field.field.replace(/_/g, ' ')}</span>
                  <div className="min-w-0 text-gray-900">
                    <span className="text-gray-500">{String(field.from ?? '—')}</span>
                    <ArrowRight className="mx-2 inline h-3.5 w-3.5 text-gray-400" />
                    <span className="font-medium">{String(field.to ?? '—')}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h4 className="font-semibold text-gray-900">Potential impact</h4>
              <p className="mt-1 text-sm text-gray-600">{detail.impact.reason}</p>
            </div>
            <FileText className="h-5 w-5 text-gray-400" />
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-sm">
            <Badge variant={detail.impact.potentially_affected ? 'warning' : 'outline'}>
              {detail.impact.approval_count} approval{detail.impact.approval_count === 1 ? '' : 's'}
            </Badge>
            <Badge variant="outline">{detail.impact.project_count} project{detail.impact.project_count === 1 ? '' : 's'}</Badge>
          </div>
          {detail.impact.current_project && (
            <div className="mt-3 rounded-lg border border-blue-200 bg-blue-50 p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">Your project</p>
              <p className="mt-1 font-medium text-blue-950">{detail.impact.current_project.project_name || 'Current project'}</p>
              <p className="mt-1 text-sm text-blue-900">
                {detail.impact.current_project.potentially_affected
                  ? `Potentially affected through ${detail.impact.current_project.matched_approvals.length} matching approval(s).`
                  : 'No matching active approval metadata was found.'}
              </p>
              {detail.impact.current_project.matched_approvals.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {detail.impact.current_project.matched_approvals.map((approval) => (
                    <Badge key={approval.approval_id} variant="outline">{approval.approval_name}</Badge>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-3 sm:flex-row">
          {detail.source.url && (
            <a href={detail.source.url} target="_blank" rel="noreferrer" className="inline-flex items-center justify-center gap-2 rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
              <ExternalLink className="h-4 w-4" />
              Open source
            </a>
          )}
          <Link href="/dashboard/regulatory" className="inline-flex items-center justify-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100">
            <Sparkles className="h-4 w-4" />
            Ask Regulatory Copilot
          </Link>
        </div>
      </CardContent>
    </Card>
  )
}

export default function RegulatoryChangeCenter({ projectId }: RegulatoryChangeCenterProps) {
  const [department, setDepartment] = useState('')
  const [effectiveStatus, setEffectiveStatus] = useState('')
  const [selectedId, setSelectedId] = useState('')
  const [search, setSearch] = useState('')
  const [selectedProject, setSelectedProject] = useState(projectId || '')

  useEffect(() => {
    if (typeof window === 'undefined') return
    const change = new URLSearchParams(window.location.search).get('change')
    if (change) setSelectedId(change)
  }, [])

  const projectsQuery = useProjects()
  const recent = useRecentRegulatoryChanges(
    {
      limit: 50,
      department: department || undefined,
      effective_status: effectiveStatus || undefined,
    },
    !selectedProject,
  )
  const projectChanges = useProjectRegulatoryChanges(selectedProject, !!selectedProject)
  const detail = useRegulatoryChange(selectedId, selectedProject || undefined, !!selectedId)

  const changes: RegulatoryChangeItem[] = selectedProject
    ? (projectChanges.data?.changes || [])
    : (recent.data?.changes || [])

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase()
    if (!query) return changes
    return changes.filter((item) =>
      [item.title, item.department, item.version, item.text_change_summary]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query)),
    )
  }, [changes, search])

  const isLoading = selectedProject ? projectChanges.isLoading : recent.isLoading
  const isError = selectedProject ? projectChanges.isError : recent.isError
  const selectedDetail = detail.data as RegulatoryChangeDetail | undefined
  const potentialImpactCount = filtered.filter((item) => item.impact.potentially_affected).length
  const activeCount = filtered.filter((item) => item.effective_status === 'ACTIVE').length

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-blue-100 bg-gradient-to-r from-blue-50 to-indigo-50 p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <div className="flex items-center gap-2 text-sm font-semibold text-blue-700">
              <History className="h-4 w-4" />
              Regulatory Change Center
            </div>
            <h2 className="mt-2 text-2xl font-bold text-gray-900">See what changed, when it takes effect, and what it may touch.</h2>
            <p className="mt-2 text-sm leading-6 text-gray-600">
              Compare versioned knowledge-base records, inspect the change breakdown, and surface potential approval/project impact before you act.
            </p>
          </div>
          <Link href="/dashboard/regulatory" className="inline-flex items-center gap-2 text-sm font-medium text-blue-700 hover:text-blue-800">
            Open full Regulatory Center <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card><CardContent className="p-5"><p className="text-sm text-gray-500">Changes shown</p><p className="mt-1 text-3xl font-extrabold tracking-tight text-gray-900">{filtered.length}</p></CardContent></Card>
        <Card><CardContent className="p-5"><p className="text-sm text-gray-500">Active now</p><p className="mt-1 text-3xl font-extrabold tracking-tight text-teal-600">{activeCount}</p></CardContent></Card>
        <Card><CardContent className="p-5"><p className="text-sm text-gray-500">Potential impact</p><p className="mt-1 text-3xl font-extrabold tracking-tight text-amber-600">{potentialImpactCount}</p></CardContent></Card>
        <Card><CardContent className="p-5"><p className="text-sm text-gray-500">View</p><p className="mt-1 text-lg font-semibold text-gray-900">{selectedProject ? 'Your project' : 'All recent'}</p></CardContent></Card>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
            {!projectId && (
              <Select value={selectedProject} onChange={(e) => { setSelectedProject(e.target.value); setSelectedId('') }} className="xl:w-72">
                <option value="">All recent changes</option>
                {(projectsQuery.data || []).map((project: any) => (
                  <option key={project.id} value={project.id}>{project.name}</option>
                ))}
              </Select>
            )}
            {!selectedProject && (
              <>
                <Select value={department} onChange={(e) => { setDepartment(e.target.value); setSelectedId('') }} className="xl:w-64">
                  <option value="">All departments</option>
                  <option value="MPCB">MPCB</option>
                  <option value="Industrial Safety">Factory</option>
                  <option value="Steam Boilers">Boiler</option>
                  <option value="Fire Services">Fire Safety</option>
                  <option value="Labour">Labour</option>
                </Select>
                <Select value={effectiveStatus} onChange={(e) => { setEffectiveStatus(e.target.value); setSelectedId('') }} className="xl:w-48">
                  <option value="">All statuses</option>
                  <option value="ACTIVE">Active</option>
                  <option value="UPCOMING">Upcoming</option>
                  <option value="EXPIRED">Expired</option>
                  <option value="UNKNOWN">Unknown</option>
                </Select>
              </>
            )}
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search regulation, department, version..."
                className="w-full rounded-xl border border-gray-300 py-2.5 pl-10 pr-4 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <Button variant="outline" onClick={() => { setSearch(''); setDepartment(''); setEffectiveStatus('') }}>
              <Filter className="mr-2 h-4 w-4" />
              Reset
            </Button>
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 text-gray-600">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          <p className="mt-4 text-sm">Loading regulatory changes...</p>
        </div>
      ) : isError ? (
        <Card><CardContent className="py-16 text-center"><AlertTriangle className="mx-auto h-10 w-10 text-amber-500" /><p className="mt-4 font-medium text-gray-900">Regulatory change data is unavailable.</p><p className="mt-1 text-sm text-gray-600">The knowledge base may not contain versioned change records yet.</p></CardContent></Card>
      ) : filtered.length === 0 ? (
        <Card><CardContent className="py-16 text-center"><CheckCircle2 className="mx-auto h-10 w-10 text-teal-600" /><p className="mt-4 font-medium text-gray-900">No matching regulatory changes found.</p><p className="mt-1 text-sm text-gray-600">Try another filter or view all recent changes.</p></CardContent></Card>
      ) : (
        <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-3">
            {filtered.map((change) => (
              <ChangeCard key={change.document_id} change={change} selected={change.document_id === selectedId} onSelect={() => setSelectedId(change.document_id === selectedId ? '' : change.document_id)} />
            ))}
          </div>
          <div>
            {selectedId ? (
              detail.isLoading ? (
                <Card><CardContent className="flex items-center gap-2 py-12 text-sm text-gray-600"><RefreshCw className="h-4 w-4 animate-spin" />Loading change details...</CardContent></Card>
              ) : detail.isError || !selectedDetail ? (
                <Card><CardContent className="py-12 text-center text-sm text-gray-600">Change details could not be loaded.</CardContent></Card>
              ) : (
                <DetailPanel detail={selectedDetail} onClose={() => setSelectedId('')} />
              )
            ) : (
              <Card className="h-full"><CardContent className="flex min-h-[340px] flex-col items-center justify-center p-8 text-center"><Calendar className="h-10 w-10 text-blue-500" /><h3 className="mt-4 font-semibold text-gray-900">Select a change</h3><p className="mt-1 max-w-sm text-sm leading-6 text-gray-600">Open a regulation update to compare versions, inspect section-level changes, and review potential impact.</p></CardContent></Card>
            )}
          </div>
        </div>
      )}

      <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 text-xs leading-5 text-gray-600">
        <strong className="text-gray-800">Prototype knowledge-base notice:</strong> regulatory change summaries and potential-impact matches are advisory. Always verify the authoritative regulation and applicable official process before acting.
      </div>
    </div>
  )
}
