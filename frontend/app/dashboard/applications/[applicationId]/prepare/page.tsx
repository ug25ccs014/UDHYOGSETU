'use client'

import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import ApplicationPreparation from '@/features/ApplicationPreparation'

export default function ApplicationPreparationPage() {
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
        <h1 className="text-3xl font-bold text-gray-900">Application Preparation</h1>
        <p className="mt-1 max-w-3xl text-gray-600">
          Review reusable business and project information, make application-specific edits, and assemble the document package before submission.
        </p>
      </div>
      <ApplicationPreparation applicationId={applicationId} />
    </div>
  )
}
