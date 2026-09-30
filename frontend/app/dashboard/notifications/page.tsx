'use client'

import Link from 'next/link'
import { Bell, Check, ChevronDown, ExternalLink, Inbox, Loader2 } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useMarkAllNotificationsRead, useMarkNotificationRead, useNotificationSummary, useNotifications } from '@/hooks/useApi'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { NotificationItem } from '@/types'

const CATEGORY_OPTIONS = [
  { value: '', label: 'All types' },
  { value: 'approval', label: 'Approvals' },
  { value: 'sla', label: 'SLA & risk' },
  { value: 'query', label: 'Queries' },
  { value: 'inspection', label: 'Inspections' },
  { value: 'grievance', label: 'Grievances' },
  { value: 'compliance', label: 'Compliance' },
  { value: 'scheme', label: 'Schemes' },
  { value: 'profile', label: 'Profile' },
  { value: 'regulatory', label: 'Regulatory updates' },
  { value: 'general', label: 'General' },
]

const SEVERITY_OPTIONS = [
  { value: '', label: 'All priorities' },
  { value: 'error', label: 'Critical' },
  { value: 'warning', label: 'Attention' },
  { value: 'info', label: 'Updates' },
  { value: 'success', label: 'Completed' },
]

function relativeTime(value?: string | null) {
  if (!value) return ''
  const diff = Math.max(0, Date.now() - new Date(value).getTime())
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return 'Just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return new Date(value).toLocaleDateString()
}

function badgeVariant(severity: string): 'success' | 'warning' | 'danger' | 'info' | 'default' {
  if (severity === 'error') return 'danger'
  if (severity === 'warning') return 'warning'
  if (severity === 'success') return 'success'
  if (severity === 'info') return 'info'
  return 'default'
}

export default function NotificationsPage() {
  const [category, setCategory] = useState('')
  const [severity, setSeverity] = useState('')
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [offset, setOffset] = useState(0)

  const queryParams = useMemo(() => ({
    category: category || undefined,
    severity: severity || undefined,
    unread_only: unreadOnly,
    limit: 25,
    offset,
  }), [category, severity, unreadOnly, offset])

  const summary = useNotificationSummary()
  const feed = useNotifications(queryParams)
  const markRead = useMarkNotificationRead()
  const markAll = useMarkAllNotificationsRead()

  const notifications: NotificationItem[] = feed.data?.notifications || []

  const resetAnd = (setter: (value: string) => void, value: string) => {
    setter(value)
    setOffset(0)
  }

  const markAllRead = async () => {
    await markAll.mutateAsync(category || undefined)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-blue-50 flex items-center justify-center">
              <Bell className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Notification Center</h1>
              <p className="mt-1 text-gray-600">One place for application, SLA, query, inspection, grievance and compliance alerts.</p>
            </div>
          </div>
        </div>
        <Button variant="outline" onClick={markAllRead} disabled={markAll.isPending || (summary.data?.unread || 0) === 0}>
          {markAll.isPending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Check className="w-4 h-4 mr-2" />}
          Mark all read
        </Button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <p className="text-sm text-gray-500">Unread</p>
          <p className="mt-1 text-3xl font-bold text-red-600">{summary.data?.unread ?? '—'}</p>
          <p className="mt-1 text-xs text-gray-500">Needs attention</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <p className="text-sm text-gray-500">Last 24 hours</p>
          <p className="mt-1 text-3xl font-bold text-blue-600">{summary.data?.recent_24h ?? '—'}</p>
          <p className="mt-1 text-xs text-gray-500">Recent activity</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <p className="text-sm text-gray-500">All notifications</p>
          <p className="mt-1 text-3xl font-bold text-gray-900">{summary.data?.total ?? '—'}</p>
          <p className="mt-1 text-xs text-gray-500">Stored in your account</p>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col lg:flex-row gap-3">
        <select value={category} onChange={(e) => resetAnd(setCategory, e.target.value)} className="h-10 rounded-md border border-gray-300 px-3 text-sm bg-white">
          {CATEGORY_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
        <select value={severity} onChange={(e) => resetAnd(setSeverity, e.target.value)} className="h-10 rounded-md border border-gray-300 px-3 text-sm bg-white">
          {SEVERITY_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
        <button
          type="button"
          onClick={() => { setUnreadOnly((value) => !value); setOffset(0) }}
          className={`h-10 inline-flex items-center justify-center px-3 rounded-md border text-sm font-medium ${unreadOnly ? 'bg-blue-50 border-blue-300 text-blue-700' : 'bg-white border-gray-300 text-gray-700'}`}
        >
          <Inbox className="w-4 h-4 mr-2" />
          Unread only
        </button>
        {(category || severity || unreadOnly) && (
          <Button variant="ghost" onClick={() => { setCategory(''); setSeverity(''); setUnreadOnly(false); setOffset(0) }}>
            Clear filters
          </Button>
        )}
      </div>

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {feed.isLoading ? (
          <div className="py-20 text-center text-gray-500" role="status" aria-live="polite"><Loader2 className="w-7 h-7 animate-spin mx-auto" /><p className="mt-3 text-sm">Loading notifications…</p></div>
        ) : feed.isError ? (
          <div className="py-20 text-center px-6">
            <Bell className="w-10 h-10 mx-auto text-gray-300" aria-hidden="true" />
            <h2 className="mt-3 font-semibold text-gray-900">Notification feed unavailable</h2>
            <p className="mt-1 text-sm text-gray-500">Check your connection and retry without losing your filters.</p>
            <Button className="mt-4" variant="outline" onClick={() => feed.refetch()} disabled={feed.isFetching}>
              {feed.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Retry
            </Button>
          </div>
        ) : notifications.length === 0 ? (
          <div className="py-20 text-center px-6">
            <Check className="w-10 h-10 mx-auto text-green-600" />
            <h2 className="mt-3 font-semibold text-gray-900">No notifications found</h2>
            <p className="mt-1 text-sm text-gray-500">Try changing your filters or continue your application journey.</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {notifications.map((item) => (
              <article key={item.id} className={`p-5 sm:p-6 ${item.is_read ? 'bg-white' : 'bg-blue-50/30'}`}>
                <div className="flex flex-col lg:flex-row lg:items-start gap-4">
                  <div className={`mt-1 w-10 h-10 shrink-0 rounded-full flex items-center justify-center ${item.severity === 'error' ? 'bg-red-100 text-red-700' : item.severity === 'warning' ? 'bg-amber-100 text-amber-700' : item.severity === 'success' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'}`}>
                    <Bell className="w-4 h-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className={`text-base text-gray-900 ${item.is_read ? 'font-medium' : 'font-semibold'}`}>{item.title}</h2>
                      {!item.is_read && <span className="w-2 h-2 rounded-full bg-blue-600" aria-label="Unread" />}
                      <Badge variant={badgeVariant(item.severity)}>{item.category.replace('_', ' ')}</Badge>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-gray-600">{item.message}</p>
                    <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-gray-500">
                      <span>{relativeTime(item.created_at)}</span>
                      {item.created_at && <span>{new Date(item.created_at).toLocaleString()}</span>}
                      {item.reference_id && <span className="font-mono text-[11px]">Ref: {item.reference_id}</span>}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2 shrink-0">
                    {!item.is_read && (
                      <Button size="sm" variant="outline" onClick={() => markRead.mutate(item.id)} disabled={markRead.isPending}>
                        <Check className="w-4 h-4 mr-1.5" /> Read
                      </Button>
                    )}
                    {item.action_path && (
                      <Link href={item.action_path} onClick={() => !item.is_read && markRead.mutate(item.id)} className="inline-flex h-8 items-center gap-1.5 rounded-md bg-blue-600 px-3 text-sm font-medium text-white hover:bg-blue-700">
                        Open <ExternalLink className="w-3.5 h-3.5" />
                      </Link>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>

      {(offset > 0 || feed.data?.has_more) && (
        <div className="flex items-center justify-between gap-3">
          <Button variant="outline" disabled={offset === 0 || feed.isFetching} onClick={() => setOffset(Math.max(0, offset - 25))}>
            Previous
          </Button>
          <span className="text-xs text-gray-500">Showing {notifications.length ? offset + 1 : 0}–{offset + notifications.length} of {feed.data?.total ?? 0}</span>
          <Button variant="outline" disabled={!feed.data?.has_more || feed.isFetching} onClick={() => setOffset(offset + 25)}>
            Next <ChevronDown className="w-4 h-4 ml-1 rotate-[-90deg]" />
          </Button>
        </div>
      )}

      <div className="rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-900">
        <strong>About these alerts:</strong> Notifications are in-app operational updates generated from UDYOGSETU activity. Government API connectivity is not assumed; prototype/simulated events are not presented as live official messages.
      </div>
    </div>
  )
}
