'use client'

import { useLanguage, TKey } from '@/lib/language'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowRight, ArrowUpRight, Building2, FileText, ShieldCheck, Loader2, UserRound,
  CalendarDays, History, Bell, MessageSquare, FlaskConical, Plus, ClipboardList, Compass,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { useProjects } from '@/hooks/useApi'
import ScrollReveal from '@/components/fx/ScrollReveal'
import SpotlightCard from '@/components/fx/SpotlightCard'
import AuroraBackground from '@/components/fx/AuroraBackground'

const quickStart = [
  { n: 1, title: 'Create a project', desc: 'Tell us about your unit', href: '/dashboard/new-project', icon: Plus },
  { n: 2, title: 'Review approvals', desc: 'See your personalised checklist', href: '/dashboard/applications', icon: ClipboardList },
  { n: 3, title: 'Explore services', desc: 'Apply for what you need', href: '/dashboard/explore', icon: Compass },
]

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

const tones = ['bg-blue-100 text-blue-600', 'bg-teal-100 text-teal-700', 'bg-sun/30 text-navy-ink', 'bg-coral/20 text-coral']

export default function DashboardHome() {
  const { t } = useLanguage()
  const router = useRouter()
  const { data, isLoading, isError, refetch, isFetching } = useProjects()
  const projects = Array.isArray(data) ? data : []

  return (
    <div className="space-y-10">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="page-title">{t('pg.dashTitle')}</h1>
          <p className="page-sub">{t('pg.dashPurpose')}</p>
        </div>
        <Button onClick={() => router.push('/dashboard/new-project')} className="w-full sm:w-auto">
          <Plus className="h-4 w-4" /> {t('pg.startNew')}
        </Button>
      </div>

      {/* Hero / quick start */}
      <ScrollReveal>
        <div className="relative isolate overflow-hidden rounded-3xl bg-navy p-6 text-cream shadow-soft sm:p-10">
          <div className="absolute inset-0 -z-10 opacity-[.10] bg-grid invert" aria-hidden="true" />
          <AuroraBackground className="-z-10 opacity-40" />
          <div className="grid items-center gap-8 lg:grid-cols-[1.1fr_1fr]">
            <div>
              <div className="eyebrow !text-sun"><span className="pulse-dot" /> {t('pg.yourJourney')}</div>
              <h2 className="mt-3 text-2xl font-extrabold leading-tight tracking-tight sm:text-3xl">{t('pg.threeSteps')}</h2>
              <p className="mt-3 max-w-md text-blue-100">
                {t('pg.threeStepsSub')}
              </p>
              <Button variant="secondary" size="lg" className="mt-6" onClick={() => router.push('/dashboard/new-project')}>
                {t('pg.getStarted')} <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
            <ol className="grid gap-3">
              {quickStart.map((s) => {
                const Icon = s.icon
                return (
                  <li key={s.n}>
                    <Link href={s.href} className="group flex items-center gap-4 rounded-2xl border border-white/15 bg-white/10 p-4 backdrop-blur transition hover:bg-white/20">
                      <span className="grid h-10 w-10 flex-none place-items-center rounded-full bg-sun text-sm font-extrabold text-navy-ink">{s.n}</span>
                      <span className="min-w-0 flex-1">
                        <span className="block font-bold">{t(`pg.qs${s.n}T` as TKey)}</span>
                        <span className="block text-sm text-blue-200">{t(`pg.qs${s.n}D` as TKey)}</span>
                      </span>
                      <Icon className="h-5 w-5 flex-none text-blue-200 transition group-hover:translate-x-0.5 group-hover:text-sun" />
                    </Link>
                  </li>
                )
              })}
            </ol>
          </div>
        </div>
      </ScrollReveal>

      {/* Projects */}
      <section aria-labelledby="projects-h">
        <div className="mb-4 flex items-center justify-between">
          <h3 id="projects-h" className="text-lg font-extrabold text-navy">{t('pg.yourProjects')}</h3>
          {projects.length > 0 && <span className="text-sm text-gray-500">{projects.length} total</span>}
        </div>
        {isLoading ? (
          <div className="flex items-center gap-2 py-8 text-gray-500" role="status" aria-live="polite">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading your projects...
          </div>
        ) : isError ? (
          <Card>
            <CardContent className="py-10 text-center">
              <p className="font-bold text-gray-900">We couldn’t load your projects.</p>
              <p className="mt-1 text-sm text-gray-600">Your projects are safe. Check your connection and try again.</p>
              <Button className="mt-4" variant="outline" onClick={() => refetch()} disabled={isFetching}>
                {isFetching ? <Loader2 className="h-4 w-4 animate-spin" /> : null}Retry
              </Button>
            </CardContent>
          </Card>
        ) : projects.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="py-12 text-center">
              <span className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-blue-100 text-blue-600"><Building2 className="h-6 w-6" /></span>
              <p className="font-bold text-gray-900">No projects yet</p>
              <p className="mt-1 text-sm text-gray-600">Create your first project to get your approval roadmap.</p>
              <Button className="mt-5" onClick={() => router.push('/dashboard/new-project')}>Create your first project</Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
            {projects.map((project, i) => (
              <ScrollReveal key={project.id} delay={(i % 3) * 0.07} className="h-full">
                <Card
                  className="group h-full cursor-pointer transition duration-200 hover:-translate-y-1 hover:shadow-lift"
                  onClick={() => router.push(`/dashboard/${project.id}`)}
                >
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="mb-3 grid h-10 w-10 place-items-center rounded-xl bg-blue-100">
                        <Building2 className="h-5 w-5 text-blue-600" />
                      </div>
                      <ArrowUpRight className="h-4 w-4 text-gray-400 transition group-hover:text-blue-500" />
                    </div>
                    <CardTitle className="capitalize">{project.name}</CardTitle>
                    <CardDescription className="capitalize">
                      {project.sector} · {[project.location_district, project.location_state].filter(Boolean).join(', ')}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-500">
                      ₹{Number(project.investment_amount || 0).toLocaleString('en-IN')}
                      {project.created_at ? ` · ${new Date(project.created_at).toLocaleDateString()}` : ''}
                    </p>
                  </CardContent>
                </Card>
              </ScrollReveal>
            ))}
          </div>
        )}
      </section>

      {/* Capabilities */}
      <section aria-labelledby="cap-h">
        <h3 id="cap-h" className="mb-1 text-lg font-extrabold text-navy">{t('pg.whatYouCanDo')}</h3>
        <p className="mb-4 text-sm text-gray-500">{t('pg.jumpAny')}</p>
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
          {capabilities.map((cap, i) => {
            const Icon = cap.icon
            return (
              <ScrollReveal key={t(`pg.cap${i}T` as TKey)} delay={(i % 3) * 0.07} className="h-full">
                <Link href={cap.href} className="group block h-full rounded-[1.25rem] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-cream">
                  <SpotlightCard className="h-full">
                    <div className="flex h-full flex-col p-5">
                      <div className="mb-3 flex items-start justify-between gap-3">
                        <div className={`grid h-11 w-11 place-items-center rounded-xl ${tones[i % tones.length]}`}><Icon className="h-5 w-5" /></div>
                        <ArrowUpRight className="h-4 w-4 text-gray-300 transition group-hover:text-blue-500" aria-hidden="true" />
                      </div>
                      <h4 className="font-bold text-navy">{cap.title}</h4>
                      <p className="mt-1 text-sm leading-relaxed text-gray-600">{t(`pg.cap${i}D` as TKey)}</p>
                    </div>
                  </SpotlightCard>
                </Link>
              </ScrollReveal>
            )
          })}
        </div>
      </section>
    </div>
  )
}
