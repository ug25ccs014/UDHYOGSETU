'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { AlertTriangle, CloudOff, UploadCloud, FileEdit } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatOfflineTimestamp, listOfflineApplicationDrafts, type OfflineDraftRecord } from '@/lib/offline'
import { useOfflineStatus } from '@/hooks/useOfflineStatus'

export default function OfflineDraftsPanel() {
  const { isOnline, pendingDrafts, conflictDrafts } = useOfflineStatus()
  const [drafts, setDrafts] = useState<OfflineDraftRecord[]>([])

  useEffect(() => {
    const refresh = () => setDrafts(listOfflineApplicationDrafts())
    refresh()
    window.addEventListener('storage', refresh)
    const timer = window.setInterval(refresh, 5000)
    return () => {
      window.removeEventListener('storage', refresh)
      window.clearInterval(timer)
    }
  }, [pendingDrafts, conflictDrafts, isOnline])

  if (drafts.length === 0) return null

  return (
    <Card className="border-blue-200 bg-blue-50/40">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            {isOnline ? <UploadCloud className="h-5 w-5 text-blue-700" /> : <CloudOff className="h-5 w-5 text-amber-700" />}
            <div>
              <CardTitle className="text-base">Saved on this device</CardTitle>
              <p className="mt-1 text-xs text-slate-600">Draft form values are kept locally. Files and government submissions are not stored offline.</p>
            </div>
          </div>
          <Badge variant={!isOnline ? 'warning' : conflictDrafts > 0 ? 'danger' : 'info'}>{!isOnline ? 'Offline' : conflictDrafts > 0 ? `${conflictDrafts} conflict${conflictDrafts === 1 ? '' : 's'}` : `${pendingDrafts} pending sync`}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        {drafts.slice(0, 5).map((draft) => (
          <div key={draft.applicationId} className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex min-w-0 items-start gap-3">
              {draft.status === 'CONFLICT' ? <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" /> : <FileEdit className="mt-0.5 h-4 w-4 shrink-0 text-blue-700" />}
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-950">{draft.approvalName || 'Application draft'}</p>
                <p className="text-xs text-slate-500">Updated {formatOfflineTimestamp(draft.updatedAt) || 'recently'} · {draft.dirtyKeys.length} edited field{draft.dirtyKeys.length === 1 ? '' : 's'}</p>
                {draft.blockedSensitiveKeys?.length ? <p className="mt-1 truncate text-xs text-amber-700">{draft.blockedSensitiveKeys.length} sensitive field{draft.blockedSensitiveKeys.length === 1 ? '' : 's'} will need review online.</p> : null}
                {draft.lastError && <p className="mt-1 truncate text-xs text-red-600">{draft.lastError}</p>}
              </div>
            </div>
            <Link href={`/dashboard/applications/${encodeURIComponent(draft.applicationId)}/prepare`}>
              <Button size="sm" variant="outline">Review draft</Button>
            </Link>
          </div>
        ))}
        {drafts.length > 5 && <p className="pt-1 text-xs text-slate-500">Showing the 5 most recent local drafts.</p>}
      </CardContent>
    </Card>
  )
}
