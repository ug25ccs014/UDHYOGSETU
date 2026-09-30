'use client'

import { useParams } from 'next/navigation'
import DocumentUploadComponent from '@/features/DocumentUpload'

export default function ProjectDocumentsPage() {
  const params = useParams()
  const projectId = params.projectId as string

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Documents</h1>
        <p className="mt-1 text-gray-600">
          Upload your industrial documents for automated validation and field extraction
        </p>
      </div>
      <DocumentUploadComponent projectId={projectId} />
    </div>
  )
}