'use client'

import { useLanguage } from '@/lib/language'
import PageHeader from '@/components/PageHeader'
import { FileCheck2 } from 'lucide-react'
import { useParams } from 'next/navigation'
import DocumentUploadComponent from '@/features/DocumentUpload'

export default function ProjectDocumentsPage() {
  const { t } = useLanguage()
  const params = useParams()
  const projectId = params.projectId as string

  return (
    <div className="space-y-6">
      <PageHeader icon={FileCheck2} title={t('pg.docsTitle')} purpose={t('pg.docsPurpose')} />
      <DocumentUploadComponent projectId={projectId} />
    </div>
  )
}