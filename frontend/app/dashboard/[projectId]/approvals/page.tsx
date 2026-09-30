'use client'

import { useParams } from 'next/navigation'
import { useState } from 'react'
import { ApplicationTracker } from '@/features/ApplicationTracker'
import { ApprovalDependencyGraph } from '@/features/ApprovalDependencyGraph'
import { Button } from '@/components/ui/button'

export default function ProjectApprovalsPage() {
  const params = useParams()
  const projectId = params.projectId as string
  const [view, setView] = useState<'table' | 'graph'>('table')

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="page-title">Approvals</h1>
          <p className="mt-1 max-w-2xl text-gray-600">See what is required, what can move in parallel, and which approval chain drives the estimated project journey.</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant={view === 'table' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setView('table')}
            className="flex-1 sm:flex-none"
          >
            Table View
          </Button>
          <Button
            variant={view === 'graph' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setView('graph')}
            className="flex-1 sm:flex-none"
          >
            Roadmap & Map
          </Button>
        </div>
      </div>

      {view === 'table' ? (
        <ApplicationTracker projectId={projectId} />
      ) : (
        <ApprovalDependencyGraph projectId={projectId} />
      )}
    </div>
  )
}