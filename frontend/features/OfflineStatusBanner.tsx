'use client'

import { CloudOff, Cloud } from 'lucide-react'
import { useOfflineStatus } from '@/hooks/useOfflineStatus'
import Link from 'next/link'
import { formatOfflineTimestamp } from '@/lib/offline'

export default function OfflineStatusBanner() {
  const { isOnline, pendingDrafts, conflictDrafts, latestCacheAt } = useOfflineStatus()

  if (isOnline && pendingDrafts === 0 && conflictDrafts === 0) return null

  if (!isOnline) {
    return (
      <div className="border-b border-amber-200 bg-amber-50 px-4 py-2.5">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 text-sm text-amber-950">
          <div className="flex min-w-0 items-center gap-2">
            <CloudOff className="h-4 w-4 shrink-0" />
            <span className="truncate">
              <span className="font-semibold">Offline mode.</span> Drafts are saved on this device; government submissions stay blocked until you are online.
            </span>
          </div>
          <span className="hidden shrink-0 text-xs text-amber-800 sm:inline">
            {latestCacheAt ? `Last local snapshot ${formatOfflineTimestamp(latestCacheAt)}` : 'No local cache yet'}
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className={`border-b px-4 py-2.5 ${conflictDrafts > 0 ? 'border-red-200 bg-red-50' : 'border-blue-200 bg-blue-50'}`}>
      <div className={`mx-auto flex max-w-7xl items-center justify-between gap-3 text-sm ${conflictDrafts > 0 ? 'text-red-950' : 'text-blue-950'}`}>
        <div className="flex min-w-0 items-center gap-2">
          <Cloud className="h-4 w-4 shrink-0" />
          <span>
            <span className="font-semibold">Connection restored.</span>{' '}
            {conflictDrafts > 0 ? `${conflictDrafts} draft${conflictDrafts === 1 ? '' : 's'} need conflict review.` : `${pendingDrafts} local draft${pendingDrafts === 1 ? '' : 's'} waiting to sync.`}
          </span>
        </div>
        <Link href="/dashboard/applications" className="inline-flex h-8 shrink-0 items-center rounded-md border-2 border-gray-300 bg-white px-3 text-sm font-medium text-gray-800 transition-colors hover:border-gray-400 hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500">Review drafts</Link>
      </div>
    </div>
  )
}
