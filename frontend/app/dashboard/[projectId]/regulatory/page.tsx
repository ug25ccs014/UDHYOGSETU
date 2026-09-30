'use client'

import { useParams } from 'next/navigation'
import RegulatoryChangeCenter from '@/features/RegulatoryChangeCenter'

export default function ProjectRegulatoryUpdatesPage() {
  const params = useParams()
  const projectId = params.projectId as string

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Regulatory Updates</h1>
        <p className="mt-1 text-gray-600">Review changes that may affect this project.</p>
      </div>
      <RegulatoryChangeCenter projectId={projectId} />
    </div>
  )
}
