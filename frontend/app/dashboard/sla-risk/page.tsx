'use client'

import { useEffect, useState } from 'react'
import SlaRiskCommandCenter from '@/features/SlaRiskCommandCenter'
import { useOfficerSlaRisk, useSlaRiskPortfolio } from '@/hooks/useApi'
import { getSessionUser } from '@/lib/auth'

export default function SlaRiskPage() {
  const [role, setRole] = useState<string>('')
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const user = getSessionUser()
    setRole(user?.role || 'ENTREPRENEUR')
    setReady(true)
  }, [])

  const officerView = role === 'OFFICER' || role === 'ADMIN'
  const portfolio = useSlaRiskPortfolio(ready && !officerView)
  const officer = useOfficerSlaRisk({}, ready && officerView)
  const data = officerView ? officer.data : portfolio.data
  const loading = officerView ? officer.isLoading : portfolio.isLoading
  const error = officerView ? officer.isError : portfolio.isError

  return (
    <SlaRiskCommandCenter
      data={data}
      loading={!ready || loading}
      error={error}
      title={officerView ? 'SLA & Smart Risk Command Center' : 'SLA & Smart Risk'}
      subtitle={officerView ? 'Prioritize applications that may need timely operational attention.' : 'See where your applications need attention before service timelines are missed.'}
      audience={officerView ? 'OFFICER' : 'ENTREPRENEUR'}
    />
  )
}
