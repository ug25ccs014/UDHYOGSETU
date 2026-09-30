'use client'

import { useLanguage } from '@/lib/language'
import PageHeader from '@/components/PageHeader'
import { Bot } from 'lucide-react'
import { useParams } from 'next/navigation'
import RegulatoryCourtilot from '@/features/RegulatoryCourtilot'

export default function ProjectCopilotPage() {
  const { t } = useLanguage()
  const params = useParams()
  const projectId = params.projectId as string

  return (
    <div className="space-y-6">
      <PageHeader icon={Bot} title={t('pg.copTitle')} purpose={t('pg.copPurpose')} />
      <RegulatoryCourtilot projectId={projectId} />
    </div>
  )
}