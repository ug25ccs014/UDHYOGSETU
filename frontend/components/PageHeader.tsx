import Link from 'next/link'
import { ChevronRight, type LucideIcon } from 'lucide-react'

/** Standard header for every dashboard page: what this is, what to do next, and the main action. */
export default function PageHeader({
  title, purpose, step, action, icon: Icon, badge, capitalize,
}: {
  title: string
  purpose?: string
  step?: string
  action?: React.ReactNode
  icon?: LucideIcon
  badge?: React.ReactNode
  capitalize?: boolean
}) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="flex min-w-0 items-start gap-4">
        {Icon && (
          <span className="hidden h-12 w-12 flex-none place-items-center rounded-2xl bg-navy text-cream shadow-card sm:grid">
            <Icon className="h-6 w-6" />
          </span>
        )}
        <div className="min-w-0">
          {step && <div className="eyebrow mb-1">{step}</div>}
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <h1 className={`page-title ${capitalize ? 'capitalize' : ''}`}>{title}</h1>
            {badge}
          </div>
          {purpose && <p className="page-sub">{purpose}</p>}
        </div>
      </div>
      {action && <div className="flex flex-none flex-wrap gap-2">{action}</div>}
    </div>
  )
}

/** Small KPI tile with an icon; `tone` is a Tailwind bg+text pair for the icon chip. */
export function StatCard({
  label, value, hint, icon: Icon, tone = 'bg-blue-100 text-blue-600',
}: {
  label: string
  value: React.ReactNode
  hint?: string
  icon?: LucideIcon
  tone?: string
}) {
  return (
    <div className="flex items-center gap-4 rounded-2xl border border-gray-200 bg-white/90 p-5 shadow-card transition duration-200 hover:-translate-y-0.5 hover:shadow-soft">
      {Icon && <span className={`grid h-12 w-12 flex-none place-items-center rounded-xl ${tone}`}><Icon className="h-6 w-6" /></span>}
      <div className="min-w-0">
        <div className="text-sm font-semibold text-gray-600">{label}</div>
        <div className="text-3xl font-extrabold leading-tight tracking-tight text-navy">{value}</div>
        {hint && <div className="text-xs text-gray-500">{hint}</div>}
      </div>
    </div>
  )
}

export function BackLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="inline-flex items-center gap-1 text-sm font-semibold text-gray-500 transition hover:text-navy">
      <ChevronRight className="h-4 w-4 rotate-180" /> {children}
    </Link>
  )
}
