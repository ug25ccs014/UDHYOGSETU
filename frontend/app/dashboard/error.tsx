'use client'

import Link from 'next/link'
import { AlertTriangle, Home, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function DashboardRouteError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="max-w-md text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-red-50">
          <AlertTriangle className="h-7 w-7 text-red-600" aria-hidden="true" />
        </div>
        <h1 className="mt-5 text-xl font-semibold text-gray-900">This workspace could not be loaded</h1>
        <p className="mt-2 text-sm leading-6 text-gray-600">
          Nothing was submitted or changed by this error. Retry the page, or return to your dashboard.
        </p>
        <div className="mt-6 flex flex-col justify-center gap-2 sm:flex-row">
          <Button onClick={reset}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Try again
          </Button>
          <Link href="/dashboard" className="inline-flex h-10 items-center justify-center rounded-md border-2 border-gray-300 bg-white px-4 text-base font-medium text-gray-800 hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500">
            <Home className="mr-2 h-4 w-4" />
            Dashboard
          </Link>
        </div>
      </div>
    </div>
  )
}
