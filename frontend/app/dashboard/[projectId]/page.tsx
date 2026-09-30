'use client'

import { useLanguage } from '@/lib/language'
import { useParams } from 'next/navigation'
import UnifiedCommandCenter from '@/features/UnifiedCommandCenter'
import Breadcrumbs from '@/components/Breadcrumbs'
import { BackLink } from '@/components/PageHeader'
import { useProject } from '@/hooks/useApi'

export default function ProjectOverviewPage() {
  const { t } = useLanguage()
  const params = useParams()
  const projectId = params.projectId as string
  const { data: project } = useProject(projectId)

  return (
    <div className="space-y-5">
      <Breadcrumbs items={[{ label: 'Projects', href: '/dashboard' }, { label: project?.name || 'Project' }]} />
      <BackLink href="/dashboard">{t('pg.backAll')}</BackLink>
      <UnifiedCommandCenter projectId={projectId} />
    </div>
  )
}
