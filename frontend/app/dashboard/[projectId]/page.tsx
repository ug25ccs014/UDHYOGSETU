'use client'

import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft } from 'lucide-react'
import UnifiedCommandCenter from '@/features/UnifiedCommandCenter'
import { Button } from '@/components/ui/button'
import Breadcrumbs from '@/components/Breadcrumbs'
import { useProject } from '@/hooks/useApi'

export default function ProjectOverviewPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.projectId as string
  const { data: project } = useProject(projectId)

  return (
    <div className="space-y-4">
      <Breadcrumbs items={[{ label: 'Projects', href: '/dashboard' }, { label: project?.name || 'Project' }]} />
      <Button variant="ghost" size="sm" onClick={() => router.push('/dashboard')}>
        <ArrowLeft className="mr-2 h-4 w-4" />
        All Projects
      </Button>
      <UnifiedCommandCenter projectId={projectId} />
    </div>
  )
}
