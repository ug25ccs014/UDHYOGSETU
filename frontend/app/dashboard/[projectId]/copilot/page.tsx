'use client'

import { useParams } from 'next/navigation'
import RegulatoryCourtilot from '@/features/RegulatoryCourtilot'

export default function ProjectCopilotPage() {
  const params = useParams()
  const projectId = params.projectId as string

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Regulatory Copilot</h1>
        <p className="mt-1 text-gray-600">
          Ask questions about approvals, compliance, and regulations
        </p>
      </div>
      <RegulatoryCourtilot projectId={projectId} />
    </div>
  )
}