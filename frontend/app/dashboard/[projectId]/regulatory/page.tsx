'use client'

import { useLanguage } from '@/lib/language'
import PageHeader from '@/components/PageHeader'
import { History } from 'lucide-react'
import { useParams } from 'next/navigation'
import RegulatoryChangeCenter from '@/features/RegulatoryChangeCenter'

export default function ProjectRegulatoryUpdatesPage() {
  const { t } = useLanguage()
  const params = useParams()
  const projectId = params.projectId as string

  return (
    <div className="space-y-6">
      <PageHeader icon={History} title={t('pg.regTitle')} purpose={t('pg.regProjectPurpose')} />
      <RegulatoryChangeCenter projectId={projectId} />
    </div>
  )
}
