'use client'

import RegulatoryChangeCenter from '@/features/RegulatoryChangeCenter'

export default function RegulatoryUpdatesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Regulatory Updates</h1>
        <p className="mt-1 text-gray-600">Track version changes in the regulatory knowledge base and see potential project impact.</p>
      </div>
      <RegulatoryChangeCenter />
    </div>
  )
}
