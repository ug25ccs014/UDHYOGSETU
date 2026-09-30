'use client'

import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft } from 'lucide-react'
import { QueryResolutionCenter } from '@/features/QueryResolutionCenter'
import { Button } from '@/components/ui/button'

export default function ApplicationQueryPage() {
  const params = useParams()
  const router = useRouter()
  const applicationId = params.applicationId as string

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" onClick={() => router.push(`/dashboard/applications/${applicationId}`)}>
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Application
      </Button>
      <div>
        <h1 className="page-title">Query & Response Center</h1>
        <p className="mt-1 text-gray-600">Understand the department query, gather evidence and prepare your response.</p>
      </div>
      <QueryResolutionCenter applicationId={applicationId} />
    </div>
  )
}
