'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'
import { ArrowLeft, Building2, CheckCircle2 } from 'lucide-react'
import AuroraBackground from '@/components/fx/AuroraBackground'

/**
 * Shared layout for /login and /register.
 * Left: navy story panel (desktop only). Right: the form, always centred and aligned.
 */
export default function AuthShell({
  title, subtitle, step, points, children, footer,
}: {
  title: string
  subtitle: string
  step?: string
  points: string[]
  children: React.ReactNode
  footer: React.ReactNode
}) {
  return (
    <main className="grid min-h-screen bg-cream lg:grid-cols-[1.05fr_1fr]">
      {/* Story panel */}
      <aside className="relative hidden overflow-hidden bg-navy p-12 text-cream lg:flex lg:flex-col lg:justify-between">
        <div className="absolute inset-0 opacity-[.10] bg-grid invert" aria-hidden="true" />
        <AuroraBackground className="opacity-40" />
        <Link href="/" className="relative z-10 flex items-center gap-2.5">
          <span className="grid h-10 w-10 place-items-center rounded-full border-2 border-cream/80 bg-white/10">
            <Building2 className="h-5 w-5" />
          </span>
          <span className="text-lg font-extrabold tracking-tight">UDYOGSETU</span>
        </Link>
        <div className="relative z-10 max-w-md">
          <h2 className="text-4xl font-extrabold leading-tight tracking-tight">
            From idea to industry, <span className="text-sun">one clear path.</span>
          </h2>
          <ul className="mt-8 space-y-4">
            {points.map((p, i) => (
              <motion.li
                key={p}
                initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.25 + i * 0.12, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                className="flex items-start gap-3 text-blue-100"
              >
                <CheckCircle2 className="mt-0.5 h-5 w-5 flex-none text-teal-100" />
                <span>{p}</span>
              </motion.li>
            ))}
          </ul>
        </div>
        <p className="relative z-10 text-xs text-blue-200">© 2026 UDYOGSETU · Smart India Hackathon prototype</p>
      </aside>

      {/* Form side */}
      <section className="relative flex items-center justify-center px-5 py-10 sm:px-8">
        <Link href="/" className="absolute left-5 top-5 inline-flex items-center gap-1.5 text-sm font-semibold text-gray-500 transition hover:text-navy sm:left-8 sm:top-8">
          <ArrowLeft className="h-4 w-4" /> Home
        </Link>
        <motion.div
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
          className="w-full max-w-md"
        >
          <div className="mb-7">
            <span className="mb-4 grid h-12 w-12 place-items-center rounded-2xl bg-navy text-cream shadow-card lg:hidden">
              <Building2 className="h-6 w-6" />
            </span>
            {step && <div className="eyebrow mb-2">{step}</div>}
            <h1 className="text-3xl font-extrabold tracking-tight text-navy">{title}</h1>
            <p className="mt-2 text-gray-600">{subtitle}</p>
          </div>
          <div className="rounded-3xl border border-gray-200 bg-white p-6 shadow-soft sm:p-8">{children}</div>
          <p className="mt-6 text-center text-sm text-gray-600">{footer}</p>
        </motion.div>
      </section>
    </main>
  )
}
