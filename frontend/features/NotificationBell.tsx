'use client'

import Link from 'next/link'
import { Bell, Check, ExternalLink, Loader2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useMarkNotificationRead, useNotifications, useUnreadNotificationCount } from '@/hooks/useApi'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { NotificationItem } from '@/types'

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

function severityClass(severity: string) {
  switch (severity) {
    case 'error': return 'bg-red-50 text-red-700 border-red-100'
    case 'warning': return 'bg-amber-50 text-amber-700 border-amber-100'
    case 'success': return 'bg-green-50 text-green-700 border-green-100'
    default: return 'bg-blue-50 text-blue-700 border-blue-100'
  }
}

export default function NotificationBell() {
  const [open, setOpen] = useState(false)
  const unread = useUnreadNotificationCount()
  const feed = useNotifications({ limit: 6 })
  const markRead = useMarkNotificationRead()
  const notifications: NotificationItem[] = feed.data?.notifications || []

  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open])

  const handleOpen = async (item: NotificationItem) => {
    if (!item.is_read) await markRead.mutateAsync(item.id)
    setOpen(false)
  }

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="sm"
        aria-label={`Notifications${unread.data?.unread ? `, ${unread.data.unread} unread` : ''}`}
        aria-expanded={open}
        aria-haspopup="dialog"
        onClick={() => setOpen((value) => !value)}
        className="relative h-10 w-10 p-0 rounded-full"
      >
        <Bell className="w-5 h-5" />
        {(unread.data?.unread || 0) > 0 && (
          <span className="absolute -right-0.5 -top-0.5 min-w-5 h-5 px-1 rounded-full bg-red-600 text-white text-[10px] font-bold flex items-center justify-center">
            {(unread.data?.unread || 0) > 99 ? '99+' : unread.data.unread}
          </span>
        )}
      </Button>

      {open && (
        <>
          <button aria-label="Close notifications" className="fixed inset-0 z-40 cursor-default" onClick={() => setOpen(false)} />
          <div role="dialog" aria-label="Recent notifications" className="absolute right-0 mt-2 z-50 w-[min(92vw,390px)] overflow-hidden rounded-xl border border-gray-200 bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
              <div>
                <p className="font-semibold text-gray-900">Notifications</p>
                <p className="text-xs text-gray-500">{unread.data?.unread || 0} unread</p>
              </div>
              <Link href="/dashboard/notifications" onClick={() => setOpen(false)} className="text-xs font-medium text-blue-600 hover:text-blue-700">
                View all
              </Link>
            </div>

            {feed.isLoading ? (
              <div className="flex items-center justify-center gap-2 py-10 text-sm text-gray-500" role="status" aria-live="polite">
                <Loader2 className="w-4 h-4 animate-spin" /> Loading alerts…
              </div>
            ) : feed.isError ? (
              <div className="px-6 py-10 text-center">
                <p className="font-medium text-gray-900">Notifications are unavailable</p>
                <p className="mt-1 text-sm text-gray-500">Open the Notification Center to retry.</p>
                <Link href="/dashboard/notifications" onClick={() => setOpen(false)} className="mt-3 inline-flex text-sm font-medium text-blue-600 hover:underline">Open Notification Center</Link>
              </div>
            ) : notifications.length === 0 ? (
              <div className="py-10 px-6 text-center">
                <Check className="mx-auto w-8 h-8 text-green-600" />
                <p className="mt-2 font-medium text-gray-900">You’re all caught up</p>
                <p className="text-sm text-gray-500 mt-1">Important application and compliance updates will appear here.</p>
              </div>
            ) : (
              <div className="max-h-[420px] overflow-y-auto divide-y divide-gray-100">
                {notifications.map((item) => (
                  <div key={item.id} className={`p-4 ${item.is_read ? 'bg-white' : 'bg-blue-50/40'}`}>
                    <div className="flex gap-3">
                      <span className={`mt-0.5 inline-flex h-2.5 w-2.5 rounded-full border ${severityClass(item.severity)}`} aria-hidden="true" />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-start justify-between gap-2">
                          <p className={`text-sm ${item.is_read ? 'font-medium' : 'font-semibold'} text-gray-900`}>{item.title}</p>
                          <span className="shrink-0 text-[11px] text-gray-400">{relativeTime(item.created_at)}</span>
                        </div>
                        <p className="mt-1 text-sm text-gray-600 line-clamp-2">{item.message}</p>
                        <div className="mt-2 flex items-center gap-2">
                          <Badge variant={item.severity === 'error' ? 'danger' : item.severity === 'warning' ? 'warning' : item.severity === 'success' ? 'success' : 'info'}>
                            {item.category.replace('_', ' ')}
                          </Badge>
                          {!item.is_read && (
                            <button className="text-[11px] font-medium text-gray-500 hover:text-gray-800" onClick={() => markRead.mutate(item.id)}>
                              Mark read
                            </button>
                          )}
                          {item.action_path && (
                            <Link href={item.action_path} onClick={() => handleOpen(item)} className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700">
                              Open <ExternalLink className="w-3 h-3" />
                            </Link>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
