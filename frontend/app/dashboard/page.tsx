'use client'

import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowRight,
  ArrowUpRight,
  Building2,
  FileText,
  ShieldCheck,
  Loader2,
  UserRound,
  CalendarDays,
  History,
  Bell,
  MessageSquare,
  FlaskConical,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { useProjects } from '@/hooks/useApi'

const capabilities = [
  { href: '/dashboard/profile', icon: UserRound, title: 'Business Profile', desc: 'Keep reusable business information and documents ready for future applications.' },
  { href: '/dashboard/applications', icon: FileText, title: 'Applications', desc: 'Track drafts, submissions, queries and approval progress in one place.' },
  { href: '/dashboard/inspections', icon: CalendarDays, title: 'Inspection Planner', desc: 'See scheduled site visits and coordination opportunities.' },
  { href: '/dashboard/sla-risk', icon: ShieldCheck, title: 'SLA & Risk', desc: 'Review timelines, risk signals and cases that need attention.' },
  { href: '/dashboard/grievances', icon: MessageSquare, title: 'Grievances', desc: 'Raise and follow application issues through an auditable workflow.' },
  { href: '/dashboard/notifications', icon: Bell, title: 'Notifications', desc: 'Review important approval, query, inspection and compliance alerts.' },
  { href: '/dashboard/regulatory', icon: History, title: 'Regulatory Updates', desc: 'Compare knowledge-base versions and review potential project impact.' },
  { href: '/dashboard/integrations', icon: ShieldCheck, title: 'Government Integrations', desc: 'See which services are simulated, guided, external or future-authorized.' },
  { href: '/dashboard/demo', icon: FlaskConical, title: 'SIH Demo Center', desc: 'Run the complete prototype walkthrough and verify the seeded journey before your presentation.' },
]
export default function DashboardHome() {
  const router = useRouter()
  const { data, isLoading, isError, refetch, isFetching } = useProjects()
  const projects = Array.isArray(data) ? data : []

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-1 text-gray-600">Manage your industrial projects and approvals</p>
        </div>
        <Button onClick={() => router.push('/dashboard/new-project')} className="w-full sm:w-auto">
          <Building2 className="w-4 h-4 mr-2" />
          Start New Project
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="flex flex-col lg:flex-row items-center gap-8 p-8 bg-gradient-to-r from-blue-600 to-indigo-700 rounded-lg">
            <div className="flex-1">
              <h2 className="text-2xl font-bold text-white">
                From Idea to Industry — One Intelligent Journey
              </h2>
              <p className="mt-2 text-blue-100">
                Set up your industrial project in a few simple steps. Answer a few questions about
                your business and UDYOGSETU will build your approval roadmap instantly.
              </p>
              <Button
                variant="secondary"
                size="lg"
                className="mt-6"
                onClick={() => router.push('/dashboard/new-project')}
              >
                Get Started
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
            <div className="hidden lg:block text-8xl">🏭</div>
          </div>
        </CardContent>
      </Card>

      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Your Projects</h3>
        {isLoading ? (
          <div className="flex items-center gap-2 text-gray-500 py-8" role="status" aria-live="polite">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading your projects...
          </div>
        ) : isError ? (
          <Card>
            <CardContent className="py-10 text-center">
              <p className="font-medium text-gray-900">We couldn’t load your projects.</p>
              <p className="mt-1 text-sm text-gray-600">Your projects are safe. Check your connection and try again.</p>
              <Button className="mt-4" variant="outline" onClick={() => refetch()} disabled={isFetching}>
                {isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Retry
              </Button>
            </CardContent>
          </Card>
        ) : projects.length === 0 ? (
          <Card>
            <CardContent className="py-10 text-center">
              <p className="text-gray-600">No projects yet.</p>
              <Button className="mt-4" onClick={() => router.push('/dashboard/new-project')}>
                Create your first project
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project) => (
              <Card
                key={project.id}
                className="cursor-pointer hover:shadow-md transition group"
                onClick={() => router.push(`/dashboard/${project.id}`)}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center mb-3">
                      <Building2 className="w-5 h-5 text-blue-600" />
                    </div>
                    <ArrowUpRight className="w-4 h-4 text-gray-400 group-hover:text-blue-600 transition" />
                  </div>
                  <CardTitle className="capitalize">{project.name}</CardTitle>
                  <CardDescription className="capitalize">
                    {project.sector} · {[project.location_district, project.location_state].filter(Boolean).join(', ')}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-500">
                    ${Number(project.investment_amount || 0).toLocaleString()}
                    {project.created_at ? ` · ${new Date(project.created_at).toLocaleDateString()}` : ''}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">What you can do</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {capabilities.map((cap) => {
            const Icon = cap.icon
            return (
              <Link key={cap.title} href={cap.href} className="group block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 rounded-lg">
                <Card className="h-full transition group-hover:-translate-y-0.5 group-hover:shadow-md group-focus-visible:ring-2 group-focus-visible:ring-blue-500">
                  <CardHeader>
                    <div className="flex items-start justify-between gap-3">
                      <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center mb-3">
                        <Icon className="w-5 h-5 text-blue-600" />
                      </div>
                      <ArrowUpRight className="w-4 h-4 text-gray-300 transition group-hover:text-blue-600" aria-hidden="true" />
                    </div>
                    <CardTitle>{cap.title}</CardTitle>
                    <CardDescription>{cap.desc}</CardDescription>
                  </CardHeader>
                </Card>
              </Link>
            )
          })}
        </div>
      </div>
    </div>
  )
}