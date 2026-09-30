'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { motion, useScroll, useTransform } from 'framer-motion'
import {
  Building2, FileSearch, ShieldCheck, Landmark, Bot, Gift, History,
  ArrowRight, ArrowDown, Sparkles, ClipboardList, Upload, Activity,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import BlurText from '@/components/fx/BlurText'
import Magnet from '@/components/fx/Magnet'
import ScrollReveal from '@/components/fx/ScrollReveal'
import SpotlightCard from '@/components/fx/SpotlightCard'
import AuroraBackground from '@/components/fx/AuroraBackground'
import Counter from '@/components/fx/Counter'
import IsoStack from '@/components/fx/IsoStack'

const features = [
  { icon: FileSearch, title: 'Intelligent Approvals', description: 'Get a personalised approval checklist based on your project.', tone: 'bg-blue-100 text-blue-600' },
  { icon: ShieldCheck, title: 'Document Intelligence', description: 'AI-powered document validation and cross-checking.', tone: 'bg-teal-100 text-teal-700' },
  { icon: Landmark, title: 'Compliance Tracking', description: 'Stay on top of post-approval compliance requirements.', tone: 'bg-sun/30 text-navy-ink' },
  { icon: Building2, title: 'Government Integration Readiness', description: 'Transparent prototype with guided, future-authorised integration paths.', tone: 'bg-coral/20 text-coral' },
  { icon: Bot, title: 'Regulatory Copilot', description: 'Ask questions about regulations and get grounded answers.', tone: 'bg-blue-100 text-blue-600' },
  { icon: Gift, title: 'Incentive Discovery', description: 'Find and apply for government schemes you qualify for.', tone: 'bg-teal-100 text-teal-700' },
  { icon: History, title: 'Regulatory Change Center', description: 'Compare regulation versions and review potential project impact.', tone: 'bg-sun/30 text-navy-ink' },
]

const steps = [
  { icon: ClipboardList, title: 'Tell us about your project', desc: 'Answer a few simple questions about your business.', you: 'You: fill a 2-minute form' },
  { icon: FileSearch, title: 'Get your approval roadmap', desc: 'We build a personalised checklist of every approval you need.', you: 'You: review the checklist' },
  { icon: Upload, title: 'Upload documents', desc: 'Documents are validated and cross-checked automatically.', you: 'You: upload & fix flagged items' },
  { icon: Activity, title: 'Track & stay compliant', desc: 'Monitor deadlines, queries and renewals in one place.', you: 'You: follow the timeline' },
]

const stats: [string, number, string][] = [
  ['Integrated modules', 7, ''],
  ['Guided steps to go live', 4, ''],
  ['Dashboard for everything', 1, ''],
]

export default function Home() {
  const [scrolled, setScrolled] = useState(false)
  const heroRef = useRef<HTMLElement>(null)
  const stepsRef = useRef<HTMLDivElement>(null)

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
  // Steps: progress line fills while section scrolls
  const { scrollYProgress: stepsP } = useScroll({ target: stepsRef, offset: ['start 70%', 'end 60%'] })

  return (
    <main className="min-h-screen overflow-x-hidden bg-cream text-gray-900">
      {/* NAV */}
      <nav className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${scrolled ? 'border-b border-gray-200 bg-cream/85 shadow-card backdrop-blur-md' : 'bg-transparent'}`}>
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 sm:px-8">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="grid h-10 w-10 place-items-center rounded-full border-2 border-navy bg-white">
              <Building2 className="h-5 w-5 text-navy" />
            </span>
            <span className="text-lg font-extrabold tracking-tight text-navy">UDYOGSETU</span>
          </Link>
          <div className="hidden items-center gap-8 text-sm font-semibold text-gray-600 md:flex">
            <a href="#how-it-works" className="transition hover:text-navy">How it works</a>
            <a href="#features" className="transition hover:text-navy">Features</a>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/login"><Button variant="outline" size="sm">Login</Button></Link>
            <Link href="/register"><Button size="sm">Get Started</Button></Link>
          </div>
        </div>
      </nav>

      {/* HERO */}
      <section ref={heroRef} className="relative isolate overflow-hidden border-b border-gray-200 pt-16">
        <AuroraBackground />
        <div className="absolute inset-0 -z-0 bg-grid [mask-image:linear-gradient(to_bottom,#000,transparent_85%)]" aria-hidden="true" />
        <motion.div style={{ y: heroY, opacity: heroFade }} className="relative z-10 mx-auto grid max-w-7xl items-center gap-10 px-5 py-16 sm:px-8 lg:grid-cols-2 lg:py-24">
          <div>
            <div className="eyebrow mb-5 rounded-full border border-gray-200 bg-white/70 px-3.5 py-1.5 backdrop-blur">
              <span className="pulse-dot" /> <Sparkles className="h-3.5 w-3.5" /> Smart India Hackathon · Prototype
            </div>
            <BlurText
              className="text-4xl font-extrabold leading-[1.02] tracking-tight text-navy sm:text-5xl lg:text-6xl"
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
          <IsoStack />
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

      {/* HOW IT WORKS */}
      <section id="how-it-works" className="scroll-mt-16 py-20 sm:py-28">
        <div className="mx-auto max-w-5xl px-5 sm:px-8">
          <ScrollReveal className="mx-auto mb-14 max-w-2xl text-center">
            <div className="eyebrow">How it works</div>
            <h2 className="mt-3 text-3xl font-extrabold tracking-tight text-navy sm:text-4xl">Four clear steps. Always know what’s next.</h2>
            <p className="mt-3 text-gray-600">Each step tells you exactly what to do, so nothing gets missed.</p>
          </ScrollReveal>

          <div ref={stepsRef} className="relative">
            {/* track + animated fill */}
            <div className="absolute bottom-6 left-6 top-6 w-0.5 rounded bg-gray-200 sm:left-1/2 sm:-translate-x-1/2" aria-hidden="true" />
            <motion.div
              className="absolute bottom-6 left-6 top-6 w-0.5 origin-top rounded bg-gradient-to-b from-blue-500 via-teal to-coral sm:left-1/2 sm:-translate-x-1/2"
              style={{ scaleY: stepsP }} aria-hidden="true"
            />
            <ol className="space-y-10">
              {steps.map((s, i) => {
                const Icon = s.icon
                const right = i % 2 === 1
                return (
                  <li key={s.title} className="relative grid grid-cols-[3rem_1fr] items-start gap-5 sm:grid-cols-2 sm:gap-16">
                    <div className="absolute left-0 top-0 grid h-12 w-12 place-items-center rounded-full border-4 border-cream bg-navy text-lg font-extrabold text-cream shadow-card sm:left-1/2 sm:-translate-x-1/2">
                      {i + 1}
                    </div>
                    <ScrollReveal className={`col-start-2 sm:col-start-auto ${right ? 'sm:col-start-2' : 'sm:col-start-1 sm:text-right'}`} y={30}>
                      <div className={`rounded-2xl border border-gray-200 bg-white/85 p-5 shadow-card ${right ? '' : 'sm:ml-auto'}`}>
                        <div className={`mb-3 flex items-center gap-2 text-navy ${right ? '' : 'sm:justify-end'}`}>
                          <Icon className="h-5 w-5 text-blue-500" />
                          <h3 className="text-lg font-bold">{s.title}</h3>
                        </div>
                        <p className="text-sm text-gray-600">{s.desc}</p>
                        <p className="mt-3 inline-block rounded-full bg-sun/30 px-3 py-1 text-xs font-bold text-navy-ink">{s.you}</p>
                      </div>
                    </ScrollReveal>
                  </li>
                )
              })}
            </ol>
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section id="features" className="scroll-mt-16 border-y border-gray-200 bg-white/60 py-20 sm:py-28">
        <div className="mx-auto max-w-7xl px-5 sm:px-8">
          <ScrollReveal className="mx-auto mb-14 max-w-2xl text-center">
            <div className="eyebrow">Features</div>
            <h2 className="mt-3 text-3xl font-extrabold tracking-tight text-navy sm:text-4xl">Everything to set up and run an industrial unit</h2>
            <p className="mt-3 text-gray-600">Built for entrepreneurs setting up in Maharashtra.</p>
          </ScrollReveal>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((f, i) => {
              const Icon = f.icon
              return (
                <ScrollReveal key={f.title} delay={(i % 3) * 0.08} className="h-full">
                  <SpotlightCard className="h-full">
                    <div className="flex h-full flex-col p-6">
                      <div className={`mb-4 grid h-12 w-12 place-items-center rounded-xl ${f.tone}`}><Icon className="h-6 w-6" /></div>
                      <h3 className="mb-1.5 text-lg font-bold text-navy">{f.title}</h3>
                      <p className="text-sm leading-relaxed text-gray-600">{f.description}</p>
                    </div>
                  </SpotlightCard>
                </ScrollReveal>
              )
            })}
          </div>
        </div>
      </section>

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
