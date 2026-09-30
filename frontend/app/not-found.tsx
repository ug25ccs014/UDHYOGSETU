'use client'

import Link from 'next/link'
import { ArrowLeft, Building2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useLanguage } from '@/lib/language'

export default function NotFound() {
  const { t } = useLanguage()
  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-16">
      <div className="max-w-md text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-50">
          <Building2 className="h-8 w-8 text-blue-600" aria-hidden="true" />
        </div>
        <p className="mt-6 text-sm font-semibold uppercase tracking-[0.18em] text-blue-600">404</p>
        <h1 className="mt-2 text-3xl font-bold text-gray-900">{t('states.notFoundTitle')}</h1>
        <p className="mt-2 text-sm leading-6 text-gray-600">{t('states.notFoundDesc')}</p>
        <Link href="/dashboard" className="mt-6 inline-flex">
          <Button>
            <ArrowLeft className="mr-2 h-4 w-4" />
            {t('states.backToDashboard')}
          </Button>
        </Link>
      </div>
    </main>
  )
}
