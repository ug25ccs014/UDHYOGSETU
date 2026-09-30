'use client'

import { useLanguage } from '@/lib/language'
import PageHeader from '@/components/PageHeader'
import { useState } from 'react'
import Link from 'next/link'
import { Search, Compass, Loader2, ExternalLink } from 'lucide-react'
import { useServices, useServiceCategories } from '@/hooks/useApi'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

const modeVariant: Record<string, 'default' | 'success' | 'warning' | 'info' | 'outline'> = {
  AUTHORIZED_API: 'success',
  PROTOTYPE_SIMULATOR: 'warning',
  GUIDED_SUBMISSION: 'info',
  GUIDED_PROTOTYPE: 'info',
  EXTERNAL_PORTAL: 'info',
  FUTURE_AUTHORIZED_API: 'outline',
}

function serviceIntegrationLabel(service: any) {
  return service.integration?.label || String(service.application_mode).replace('_', ' ')
}

export default function ExplorePage() {
  const { t } = useLanguage()
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')
  const [applicationMode, setApplicationMode] = useState('')
  const { data: categories } = useServiceCategories()
  const { data: services, isLoading, isError, refetch, isFetching } = useServices({
    q: q || undefined,
    category: category || undefined,
    application_mode: applicationMode || undefined,
  })

  const categoryOptions: string[] = categories?.categories || []

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Compass}
        title={t('pg.exploreTitle')}
        purpose={t('pg.explorePurpose')}
      />

      <div className="space-y-4 rounded-2xl border border-gray-200 bg-white/90 p-5 shadow-card">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search services, e.g. factory licence, GST, boiler..."
              className="pl-10"
            />
          </div>
          <Select value={category} onChange={(e) => setCategory(e.target.value)} className="md:w-64">
            <option value="">All categories</option>
            {categoryOptions.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </Select>
          <Select
            value={applicationMode}
            onChange={(e) => setApplicationMode(e.target.value)}
            className="md:w-56"
          >
            <option value="">All modes</option>
            <option value="INTEGRATED">Prototype / Integrated flow</option>
            <option value="GUIDED">Guided</option>
            <option value="REDIRECT">External portal</option>
            <option value="DEMO">Demo</option>
          </Select>
        </div>
      </div>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-24 text-gray-600" role="status" aria-live="polite">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          <p className="mt-4 text-sm">Loading services...</p>
        </div>
      ) : isError ? (
        <Card>
          <CardContent className="py-16 text-center">
            <Compass className="w-10 h-10 mx-auto text-gray-300" aria-hidden="true" />
            <p className="mt-4 font-medium text-gray-900">Government service catalogue unavailable</p>
            <p className="mt-1 text-sm text-gray-600">Check your connection and try again.</p>
            <Button className="mt-4" variant="outline" onClick={() => refetch()} disabled={isFetching}>
              {isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Retry
            </Button>
          </CardContent>
        </Card>
      ) : !services || services.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <Compass className="w-10 h-10 mx-auto text-gray-300" />
            <p className="mt-4 text-gray-600">No services match your filters.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {services.map((service: any) => {
            const ModeIcon =
              service.application_mode === 'REDIRECT' ? ExternalLink : Compass
            return (
              <Link key={service.id} href={`/dashboard/explore/${service.slug}`}>
                <Card className="h-full cursor-pointer hover:shadow-md transition">
                  <CardHeader>
                    <div className="flex items-start justify-between mb-2">
                      <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center">
                        <ModeIcon className="w-5 h-5 text-blue-600" />
                      </div>
                      {service.is_demo && <Badge variant="warning">Demo</Badge>}
                    </div>
                    <CardTitle className="capitalize text-base">{service.name}</CardTitle>
                    <CardDescription className="capitalize">
                      {service.category} · {service.authority}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-sm text-gray-600 line-clamp-2">{service.description}</p>
                    <div className="flex flex-wrap gap-2">
                      <Badge variant={modeVariant[service.integration?.classification] || 'outline'}>
                        {serviceIntegrationLabel(service)}
                      </Badge>
                      {service.sla_days ? (
                        <Badge variant="outline">{service.sla_days} day SLA</Badge>
                      ) : null}
                      <Badge variant="outline">{service.service_type}</Badge>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}