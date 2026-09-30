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

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/dashboard/explore', label: 'Explore Services', icon: Compass },
  { href: '/dashboard/applications', label: 'Applications', icon: ClipboardList },
  { href: '/dashboard/profile', label: 'Business Profile', icon: UserRound },
  { href: '/dashboard/inspections', label: 'Inspections', icon: CalendarDays },
  { href: '/dashboard/sla-risk', label: 'SLA & Risk', icon: ShieldAlert },
  { href: '/dashboard/grievances', label: 'Grievances', icon: MessageSquare },
  { href: '/dashboard/notifications', label: 'Notifications', icon: Bell },
  { href: '/dashboard/regulatory', label: 'Regulatory Updates', icon: History },
  { href: '/dashboard/integrations', label: 'Government Integrations', icon: ShieldCheck },
  { href: '/dashboard/demo', label: 'SIH Demo Center', icon: FlaskConical },
  { href: '/dashboard/new-project', label: 'New Project', icon: Plus },
]

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

  const sidebar = (
    <>
      <div className="flex items-center justify-between p-6 border-b border-gray-200">
        <Link
          href="/dashboard"
          onClick={() => setSidebarOpen(false)}
          className="flex items-center gap-2"
        >
          <div className="inline-flex items-center justify-center w-10 h-10 bg-blue-600 rounded-xl">
            <Building2 className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold text-gray-900">UDYOGSETU</span>
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

      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const active = item.href === '/dashboard'
            ? pathname === '/dashboard'
            : pathname === item.href || pathname.startsWith(`${item.href}/`)
          const Icon = item.icon
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setSidebarOpen(false)}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition',
                active
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-100',
              )}
            >
              <Icon className="w-4.5 h-4.5" />
              {item.label}
            </Link>
          )
        })}

        {(user?.role === 'OFFICER' || user?.role === 'ADMIN') && (
          <Link
            href="/dashboard/officer"
            aria-current={pathname === '/dashboard/officer' || pathname.startsWith('/dashboard/officer/') ? 'page' : undefined}
            onClick={() => setSidebarOpen(false)}
            className={cn(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition',
              pathname === '/dashboard/officer' || pathname.startsWith('/dashboard/officer/')
                ? 'bg-blue-50 text-blue-700'
                : 'text-gray-700 hover:bg-gray-100',
            )}
          >
            <ShieldAlert className="w-4.5 h-4.5" />
            Officer Command Center
          </Link>
        )}

        {isProjectContext && (
          <>
            <div className="pt-4 pb-2">
              <p className="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Project
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
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition',
                    active
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-100',
                  )}
                >
                  <Icon className="w-4.5 h-4.5" />
                  {item.label}
                </Link>
              )
            })}
          </>
        )}
      </nav>

      <div className="p-4 border-t border-gray-200 space-y-2">
        <div className="flex items-center gap-3 px-3 py-2">
          <div className="w-9 h-9 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-semibold">
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
    <div className="min-h-screen bg-gray-50">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-md focus:bg-gray-900 focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-white">Skip to main content</a>
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside className="fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-gray-200 flex-col transition-transform duration-200 lg:flex hidden">
        {sidebar}
      </aside>

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-gray-200 flex flex-col transition-transform duration-200 lg:hidden',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        {sidebar}
      </aside>

      <main id="main-content" tabIndex={-1} className="lg:ml-64 min-h-screen outline-none">
        <div className="hidden lg:flex sticky top-0 z-30 h-14 items-center justify-end px-6 bg-white/95 backdrop-blur border-b border-gray-200">
          <NotificationBell />
        </div>
        <div className="lg:hidden sticky top-0 z-30 flex items-center justify-between px-4 py-3 bg-white border-b border-gray-200">
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="inline-flex items-center justify-center w-9 h-9 bg-blue-600 rounded-xl">
              <Building2 className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-bold text-gray-900">UDYOGSETU</span>
          </Link>
          <div className="flex items-center gap-1">
            <NotificationBell />
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="inline-flex items-center justify-center w-10 h-10 rounded-lg text-gray-600 hover:bg-gray-100"
              aria-label="Open menu"
            >
              <Menu className="w-6 h-6" />
            </button>
          </div>
        </div>
        <OfflineStatusBanner />
        <div className="p-4 sm:p-6 lg:p-8">
          <ErrorBoundary>{children}</ErrorBoundary>
        </div>
      </main>
    </div>
  )
}