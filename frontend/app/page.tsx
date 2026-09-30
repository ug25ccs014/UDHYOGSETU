'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { motion, useScroll, useTransform } from 'framer-motion'
import { Building2, ArrowRight, ArrowDown, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import BlurText from '@/components/fx/BlurText'
import Magnet from '@/components/fx/Magnet'
import ScrollReveal from '@/components/fx/ScrollReveal'
import AuroraBackground from '@/components/fx/AuroraBackground'
import Counter from '@/components/fx/Counter'
import GlassStack from '@/components/fx/GlassStack'
import HowItWorks from '@/components/landing/HowItWorks'

const stats: [string, number, string][] = [
  ['Integrated modules', 7, ''],
  ['Guided steps to go live', 4, ''],
  ['Dashboard for everything', 1, ''],
]

export default function Home() {
  const [scrolled, setScrolled] = useState(false)
  const heroRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 8)
    on()
    window.addEventListener('scroll', on, { passive: true })
    return () => window.removeEventListener('scroll', on)
  }, [])

  // Hero parallax: content drifts up & fades as you scroll away
  const { scrollYProgress: heroP } = useScroll({ target: heroRef, offset: ['start start', 'end start'] })
  const heroY = useTransform(heroP, [0, 1], [0, 90])
  const heroFade = useTransform(heroP, [0, 0.8], [1, 0.2])

  return (
    <main className="min-h-screen overflow-x-hidden bg-cream text-gray-900">
      {/* NAV */}
      <nav className={`fixed inset-x-0 top-0 z-50 border-b-4 border-sun bg-gradient-to-r from-navy via-navy-2 to-navy text-cream transition-shadow duration-300 ${scrolled ? 'shadow-lift' : 'shadow-card'}`}>
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 sm:px-8 lg:pl-20 lg:pr-10">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="grid h-10 w-10 place-items-center rounded-full border-2 border-cream/70 bg-white/10">
              <Building2 className="h-5 w-5 text-cream" />
            </span>
            <span className="text-lg font-extrabold tracking-tight text-cream">UDYOGSETU</span>
          </Link>
          <div className="hidden items-center gap-8 text-sm font-semibold text-blue-100 md:flex">
            <a href="#how-it-works" className="transition hover:text-white">How it works</a>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/login"><Button variant="outline" size="sm" className="border-white/30 bg-white/10 text-cream hover:border-white/50 hover:bg-white/20">Login</Button></Link>
            <Link href="/register"><Button variant="secondary" size="sm">Get Started</Button></Link>
          </div>
        </div>
      </nav>

      {/* HERO */}
      <section ref={heroRef} className="relative isolate flex min-h-screen flex-col overflow-hidden border-b border-gray-200 pt-[68px]">
        <AuroraBackground />
        <div className="absolute inset-0 -z-0 bg-grid [mask-image:linear-gradient(to_bottom,#000,transparent_85%)]" aria-hidden="true" />
        <motion.div style={{ y: heroY, opacity: heroFade }} className="relative z-10 mx-auto my-auto grid w-full max-w-7xl items-center gap-8 px-5 py-6 sm:px-8 lg:grid-cols-[1fr_1.15fr] lg:gap-10 lg:pl-20 lg:pr-10 lg:py-8">
          <div>
            <div className="eyebrow mb-5 rounded-full border border-gray-200 bg-white/70 px-3.5 py-1.5 backdrop-blur">
              <span className="pulse-dot" /> <Sparkles className="h-3.5 w-3.5" /> Smart India Hackathon · Prototype
            </div>
            <BlurText
              className="text-4xl font-extrabold leading-[1.02] tracking-tight text-navy sm:text-5xl lg:text-[2.75rem] xl:text-5xl"
              segments={[{ text: 'From Idea to Industry' }, { text: 'One Intelligent Journey', gradient: true }]}
            />
            <motion.p
              className="mt-6 max-w-xl text-base leading-relaxed text-gray-600 sm:text-lg"
              initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6, duration: 0.6 }}
            >
              Understand approvals, prepare documents, track applications, stay compliant and discover government support — all from one place.
            </motion.p>
            <motion.div
              className="mt-8 flex flex-wrap items-center gap-3"
              initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.75, duration: 0.6 }}
            >
              <Magnet>
                <Link href="/register"><Button size="lg">Start your project <ArrowRight className="h-4 w-4" /></Button></Link>
              </Magnet>
              <a href="#how-it-works"><Button size="lg" variant="outline">See how it works <ArrowDown className="h-4 w-4" /></Button></a>
            </motion.div>
            <p className="mt-5 text-sm text-gray-500">Free to try · No government login needed · Takes about 2 minutes to start</p>
          </div>
          <GlassStack />
        </motion.div>
      </section>

      {/* STATS */}
      <section className="border-b border-gray-200 bg-white/60">
        <div className="mx-auto grid max-w-7xl grid-cols-3 gap-4 px-5 py-10 text-center sm:px-8">
          {stats.map(([label, v, s]) => (
            <ScrollReveal key={label}>
              <div className="text-4xl font-extrabold tracking-tight text-navy sm:text-5xl"><Counter value={v} suffix={s} /></div>
              <div className="mt-1 text-xs font-semibold uppercase tracking-wider text-gray-500 sm:text-sm">{label}</div>
            </ScrollReveal>
          ))}
        </div>
      </section>

      <HowItWorks />

      {/* CTA */}
      <section className="relative isolate overflow-hidden bg-navy py-20 text-center sm:py-24">
        <div className="absolute inset-0 opacity-[.12] bg-grid [background-size:44px_44px] invert" aria-hidden="true" />
        <div className="relative z-10 mx-auto max-w-3xl px-5 sm:px-8">
          <ScrollReveal>
            <h2 className="text-3xl font-extrabold tracking-tight text-cream sm:text-4xl">Ready to streamline your approvals?</h2>
            <p className="mt-3 text-lg text-blue-200">Join entrepreneurs across Maharashtra using UDYOGSETU.</p>
            <div className="mt-8"><Magnet><Link href="/register"><Button size="lg" variant="secondary">Get started now <ArrowRight className="h-4 w-4" /></Button></Link></Magnet></div>
          </ScrollReveal>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="bg-navy-ink py-12 text-sm text-blue-200">
        <div className="mx-auto grid max-w-7xl gap-8 px-5 sm:px-8 md:grid-cols-4">
          <div>
            <div className="mb-3 flex items-center gap-2 font-bold text-cream"><Building2 className="h-5 w-5" /> UDYOGSETU</div>
            <p>An intelligent platform helping entrepreneurs navigate industrial approvals and compliance.</p>
          </div>
          <div>
            <h4 className="mb-3 font-bold text-cream">Quick links</h4>
            <ul className="space-y-2">
              <li><a href="#how-it-works" className="hover:text-white">How it works</a></li>
              <li><Link href="/login" className="hover:text-white">Login</Link></li>
              <li><Link href="/register" className="hover:text-white">Create account</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="mb-3 font-bold text-cream">Project note</h4>
            <p>This is a prototype journey. Government API access is not assumed.</p>
          </div>
          <div>
            <h4 className="mb-3 font-bold text-cream">Contact</h4>
            <p>support@udyogsetu.gov.in</p>
          </div>
        </div>
        <p className="mx-auto mt-10 max-w-7xl border-t border-white/10 px-5 pt-6 text-center text-xs sm:px-8">© 2026 UDYOGSETU · Smart India Hackathon prototype</p>
      </footer>
    </main>
  )
}
