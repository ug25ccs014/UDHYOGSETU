'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  Building2,
  LayoutDashboard,
  FileText,
  FolderOpen,
  Bot,
  ShieldCheck,
  Gift,
  LogOut,
  Plus,
  Compass,
  ClipboardList,
  Menu,
  X,
  UserRound,
  CalendarDays,
  ShieldAlert,
  MessageSquare,
  Bell,
  History,
  FlaskConical,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { getSessionUser, isTokenExpired, logout } from '@/lib/auth'
import NotificationBell from '@/features/NotificationBell'
import OfflineStatusBanner from '@/features/OfflineStatusBanner'

const navGroups = [
  {
    label: 'Start here',
    items: [
      { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { href: '/dashboard/new-project', label: 'New Project', icon: Plus },
      { href: '/dashboard/explore', label: 'Explore Services', icon: Compass },
    ],
  },
  {
    label: 'My work',
    items: [
      { href: '/dashboard/applications', label: 'Applications', icon: ClipboardList },
      { href: '/dashboard/profile', label: 'Business Profile', icon: UserRound },
      { href: '/dashboard/inspections', label: 'Inspections', icon: CalendarDays },
    ],
  },
  {
    label: 'Stay on track',
    items: [
      { href: '/dashboard/sla-risk', label: 'SLA & Risk', icon: ShieldAlert },
      { href: '/dashboard/grievances', label: 'Grievances', icon: MessageSquare },
      { href: '/dashboard/notifications', label: 'Notifications', icon: Bell },
      { href: '/dashboard/regulatory', label: 'Regulatory Updates', icon: History },
    ],
  },
  {
    label: 'More',
    items: [
      { href: '/dashboard/integrations', label: 'Government Integrations', icon: ShieldCheck },
      { href: '/dashboard/demo', label: 'SIH Demo Center', icon: FlaskConical },
    ],
  },
]
const navItems = navGroups.flatMap((g) => g.items)

// Top-level dashboard segments that are NOT a project id.
const reservedSegments = new Set(['new-project', 'explore', 'applications', 'profile', 'inspections', 'sla-risk', 'grievances', 'notifications', 'regulatory', 'integrations', 'demo'])

const projectNavItems = [
  { key: '', label: 'Command Center', icon: FolderOpen },
  { key: 'approvals', label: 'Approvals', icon: FileText },
  { key: 'documents', label: 'Documents', icon: FileText },
  { key: 'compliance', label: 'Compliance', icon: ShieldCheck },
  { key: 'copilot', label: 'Regulatory Copilot', icon: Bot },
  { key: 'schemes', label: 'Schemes & Support', icon: Gift },
  { key: 'regulatory', label: 'Regulatory Updates', icon: History },
  { key: 'simulate', label: 'Scenario Simulator', icon: FlaskConical },
]

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const [user, setUser] = useState<{ name: string; role: string } | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    setSidebarOpen(false)
  }, [pathname])

  const projectMatch = pathname.match(/^\/dashboard\/([^/]+)(?:\/([^/]+))?/)
  const currentProjectId =
    projectMatch && !reservedSegments.has(projectMatch[1]) ? projectMatch[1] : undefined
  const currentProjectTab = currentProjectId ? projectMatch?.[2] || '' : ''

  useEffect(() => {
    if (isTokenExpired()) {
      logout()
      return
    }
    const sessionUser = getSessionUser()
    if (sessionUser) {
      setUser({ name: sessionUser.name, role: sessionUser.role })
    }
  }, [router])

  const handleLogout = () => {
    logout()
  }

  const isProjectContext = !!currentProjectId
  const currentTitle = isProjectContext
    ? projectNavItems.find((i) => i.key === currentProjectTab)?.label ?? 'Project'
    : [...navItems].sort((a, b) => b.href.length - a.href.length).find((i) => i.href === '/dashboard' ? pathname === '/dashboard' : pathname === i.href || pathname.startsWith(`${i.href}/`))?.label
      ?? (pathname.startsWith('/dashboard/officer') ? 'Officer Command Center' : 'Dashboard')

  const sidebar = (
    <>
      <div className="flex h-16 items-center justify-between border-b border-gray-200 px-5">
        <Link
          href="/dashboard"
          onClick={() => setSidebarOpen(false)}
          className="flex items-center gap-2"
        >
          <span className="grid h-10 w-10 place-items-center rounded-full border-2 border-navy bg-white">
            <Building2 className="h-5 w-5 text-navy" />
          </span>
          <span className="text-lg font-extrabold tracking-tight text-navy">UDYOGSETU</span>
        </Link>
        <button
          type="button"
          onClick={() => setSidebarOpen(false)}
          className="lg:hidden inline-flex items-center justify-center w-9 h-9 rounded-lg text-gray-500 hover:bg-gray-100"
          aria-label="Close sidebar"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <nav className="flex-1 space-y-5 overflow-y-auto px-4 py-5" aria-label="Main navigation">
        {navGroups.map((group) => (
          <div key={group.label}>
            <p className="mb-1.5 px-3 text-[11px] font-extrabold uppercase tracking-[.16em] text-gray-400">{group.label}</p>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const active = item.href === '/dashboard'
                  ? pathname === '/dashboard'
                  : pathname === item.href || pathname.startsWith(`${item.href}/`)
                const Icon = item.icon
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={active ? 'page' : undefined}
                    onClick={() => setSidebarOpen(false)}
                    className={cn(
                      'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition-all duration-200',
                      active ? 'bg-navy text-cream shadow-card' : 'text-gray-700 hover:bg-white hover:text-navy hover:translate-x-0.5',
                    )}
                  >
                    <Icon className={cn('h-[18px] w-[18px] flex-none', active ? 'text-sun' : 'text-gray-400')} />
                    {item.label}
                  </Link>
                )
              })}
            </div>
          </div>
        ))}

        {(user?.role === 'OFFICER' || user?.role === 'ADMIN') && (
          <Link
            href="/dashboard/officer"
            aria-current={pathname === '/dashboard/officer' || pathname.startsWith('/dashboard/officer/') ? 'page' : undefined}
            onClick={() => setSidebarOpen(false)}
            className={cn(
              'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition-all duration-200',
              pathname === '/dashboard/officer' || pathname.startsWith('/dashboard/officer/')
                ? 'bg-navy text-cream shadow-card'
                : 'text-gray-700 hover:bg-white hover:text-navy',
            )}
          >
            <ShieldAlert className="h-[18px] w-[18px] flex-none" />
            Officer Command Center
          </Link>
        )}

        {isProjectContext && (
          <>
            <div className="pt-4 pb-2">
              <p className="px-3 text-[11px] font-extrabold uppercase tracking-[.16em] text-teal-700">
                This project
              </p>
            </div>
            {projectNavItems.map((item) => {
              const active = currentProjectTab === item.key
              const Icon = item.icon
              return (
                <Link
                  key={item.key}
                  href={`/dashboard/${currentProjectId}${item.key ? `/${item.key}` : ''}`}
                  aria-current={active ? 'page' : undefined}
                  onClick={() => setSidebarOpen(false)}
                  className={cn(
                    'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition-all duration-200',
                    active
                      ? 'bg-navy text-cream shadow-card'
                      : 'text-gray-700 hover:bg-white hover:text-navy',
                  )}
                >
                  <Icon className="h-[18px] w-[18px] flex-none" />
                  {item.label}
                </Link>
              )
            })}
          </>
        )}
      </nav>

      <div className="space-y-2 border-t border-gray-200 p-4">
        <div className="flex items-center gap-3 px-3 py-2">
          <div className="h-9 w-9 rounded-full bg-navy text-cream flex items-center justify-center text-sm font-bold">
            {(user?.name?.[0] || 'U').toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate capitalize">{user?.name}</p>
            <p className="text-xs text-gray-500">
              {user?.role === 'OFFICER' ? 'Officer' : 'Entrepreneur'}
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start text-gray-600"
          onClick={handleLogout}
        >
          <LogOut className="w-4 h-4 mr-2" />
          Logout
        </Button>
      </div>
    </>
  )

  return (
    <div className="min-h-screen bg-cream">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-md focus:bg-gray-900 focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-white">Skip to main content</a>
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside className="fixed inset-y-0 left-0 z-50 hidden w-64 flex-col border-r border-gray-200 bg-gray-100/60 backdrop-blur lg:flex">
        {sidebar}
      </aside>

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-gray-200 bg-cream shadow-lift transition-transform duration-300 ease-out lg:hidden',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        {sidebar}
      </aside>

      <main id="main-content" tabIndex={-1} className="lg:ml-64 min-h-screen outline-none">
        <div className="sticky top-0 z-30 hidden h-16 items-center justify-between border-b border-gray-200 bg-cream/85 px-8 backdrop-blur-md lg:flex">
          <div className="min-w-0">
            <p className="text-[11px] font-extrabold uppercase tracking-[.16em] text-gray-400">{isProjectContext ? 'Project' : 'UDYOGSETU'}</p>
            <p className="truncate text-sm font-bold text-navy">{currentTitle}</p>
          </div>
          <NotificationBell />
        </div>
        <div className="sticky top-0 z-30 flex items-center justify-between border-b border-gray-200 bg-cream/90 px-4 py-3 backdrop-blur-md lg:hidden">
          <Link href="/dashboard" className="flex items-center gap-2">
            <span className="grid h-9 w-9 place-items-center rounded-full border-2 border-navy bg-white">
              <Building2 className="h-4 w-4 text-navy" />
            </span>
            <span className="text-base font-extrabold tracking-tight text-navy">UDYOGSETU</span>
          </Link>
          <div className="flex items-center gap-1">
            <NotificationBell />
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="inline-flex h-10 w-10 items-center justify-center rounded-xl text-gray-600 hover:bg-white"
              aria-label="Open menu"
            >
              <Menu className="w-6 h-6" />
            </button>
          </div>
        </div>
        <OfflineStatusBanner />
        <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <div key={pathname} className="animate-view-in">
            <ErrorBoundary>{children}</ErrorBoundary>
          </div>
        </div>
      </main>
    </div>
  )
}