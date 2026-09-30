'use client'

import { Loader2 } from 'lucide-react'
import { useLanguage } from '@/lib/language'

export default function DashboardLoading() {
  const { t } = useLanguage()
  return (
    <div className="flex min-h-[50vh] items-center justify-center" role="status" aria-live="polite" aria-label={t('states.loadingLabel')}>
      <div className="flex flex-col items-center text-center text-gray-500">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50">
          <Loader2 className="h-6 w-6 animate-spin text-blue-600" aria-hidden="true" />
        </div>
        <p className="mt-4 text-sm font-medium text-gray-700">{t('states.loadingTitle')}</p>
        <p className="mt-1 text-xs text-gray-500">{t('states.loadingDesc')}</p>
      </div>
    </div>
  )
}
