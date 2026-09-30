'use client'

import { useEffect, useState } from 'react'
import { countOfflineDraftConflicts, countPendingOfflineDrafts, latestOfflineCacheTimestamp } from '@/lib/offline'

function readOfflineStatus() {
  return {
    isOnline: typeof navigator === 'undefined' ? true : navigator.onLine,
    pendingDrafts: countPendingOfflineDrafts(),
    conflictDrafts: countOfflineDraftConflicts(),
    latestCacheAt: latestOfflineCacheTimestamp(),
  }
}

export function useOfflineStatus() {
  const [state, setState] = useState(readOfflineStatus)

  useEffect(() => {
    const refresh = () => setState(readOfflineStatus())
    window.addEventListener('online', refresh)
    window.addEventListener('offline', refresh)
    window.addEventListener('storage', refresh)
    const timer = window.setInterval(refresh, 5000)
    return () => {
      window.removeEventListener('online', refresh)
      window.removeEventListener('offline', refresh)
      window.removeEventListener('storage', refresh)
      window.clearInterval(timer)
    }
  }, [])

  return state
}
