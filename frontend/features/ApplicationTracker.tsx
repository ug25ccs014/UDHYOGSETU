'use client'

import React, { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { useProjectApprovals } from '@/hooks/useApi'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

interface ApplicationTrackerProps {
  projectId: string
}

const statusFilter = ['ALL', 'SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'QUERY_RAISED']

function getStatusVariant(status: string): 'success' | 'danger' | 'default' | 'warning' | 'info' | 'outline' {
  switch (status) {
    case 'APPROVED':
      return 'success'
    case 'REJECTED':
      return 'danger'
    case 'QUERY_RAISED':
      return 'warning'
    case 'INSPECTION':
      return 'info'
    case 'SUBMITTED':
    case 'UNDER_REVIEW':
      return 'default'
    default:
      return 'outline'
  }
}

function getRiskVariant(risk: string): 'danger' | 'warning' | 'success' | 'outline' {
  switch (risk) {
    case 'HIGH':
      return 'danger'
    case 'MEDIUM':
      return 'warning'
    case 'LOW':
      return 'success'
    default:
      return 'outline'
  }
}

export function ApplicationTracker({ projectId }: ApplicationTrackerProps) {
  const { data: approvals, isLoading, isError } = useProjectApprovals(projectId)
  const [filterStatus, setFilterStatus] = useState('ALL')

  const filteredApprovals =
    filterStatus === 'ALL' ? approvals : approvals?.filter((a: any) => a.status === filterStatus)

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-gray-600">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        <p className="mt-4 text-sm">Loading applications...</p>
      </div>
    )
  }

  if (isError || !approvals) {
    return (
      <div className="py-24 text-center">
        <p className="text-lg text-gray-900">Unable to load applications</p>
        <p className="mt-2 text-gray-600">
          Run the approval analysis to generate your checklist.
        </p>
      </div>
    )
  }

  const approved = approvals.filter((a: any) => a.status === 'APPROVED').length
  const underReview = approvals.filter((a: any) => a.status === 'UNDER_REVIEW').length
  const submitted = approvals.filter((a: any) => a.status === 'SUBMITTED').length

  const stats = [
    { label: 'Total Applications', value: approvals.length, color: 'text-blue-600' },
    { label: 'Approved', value: approved, color: 'text-green-600' },
    { label: 'Under Review', value: underReview, color: 'text-blue-600' },
    { label: 'Submitted', value: submitted, color: 'text-yellow-600' },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map((stat, idx) => (
          <div key={idx} className="bg-white border border-gray-200 rounded-lg p-5">
            <div className="text-sm text-gray-600">{stat.label}</div>
            <div className={`text-3xl font-bold mt-1 ${stat.color}`}>{stat.value}</div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        {statusFilter.map((status) => (
          <Button
            key={status}
            variant={filterStatus === status ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilterStatus(status)}
          >
            {status.replace('_', ' ')}
          </Button>
        ))}
      </div>

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Approval</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Department</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Status</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Processing</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Risk</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredApprovals && filteredApprovals.length > 0 ? (
                filteredApprovals.map((approval: any) => (
                  <tr key={approval.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="font-medium text-gray-900">{approval.name}</div>
                      <div className="text-xs text-gray-500 mt-0.5">
                        {approval.is_mandatory ? 'Mandatory' : 'Optional'}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">{approval.department}</td>
                    <td className="px-6 py-4">
                      <Badge variant={getStatusVariant(approval.status)}>
                        {approval.status.replace('_', ' ')}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {approval.estimated_processing_days
                        ? `${approval.estimated_processing_days} days`
                        : '—'}
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant={getRiskVariant(approval.risk_level)}>
                        {approval.risk_level} Risk
                      </Badge>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-gray-600">
                    No applications found for this filter
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default ApplicationTracker