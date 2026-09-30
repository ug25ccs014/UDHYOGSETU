'use client'

import { useLanguage } from '@/lib/language'
import PageHeader from '@/components/PageHeader'
import { History } from 'lucide-react'
import RegulatoryChangeCenter from '@/features/RegulatoryChangeCenter'

export default function RegulatoryUpdatesPage() {
  const { t } = useLanguage()
  return (
    <div className="space-y-6">
      <PageHeader icon={History} title={t('pg.regTitle')} purpose={t('pg.regPurpose')} />
      <RegulatoryChangeCenter />
    </div>
  )
}
