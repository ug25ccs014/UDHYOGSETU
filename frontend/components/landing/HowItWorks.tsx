'use client'

import { useRef } from 'react'
import { motion, useScroll } from 'framer-motion'
import { ClipboardList, FileSearch, Upload, Activity, Check } from 'lucide-react'
import ScrollReveal from '@/components/fx/ScrollReveal'

const steps = [
  { icon: ClipboardList, tone: 'bg-blue-100 text-blue-600', title: 'Tell us about your project', desc: 'Answer a few simple questions about your business so we can understand what you are setting up.', bullets: ['Sector and type of unit', 'Location and investment size', 'Takes about 2 minutes'], you: 'You: fill a 2-minute form' },
  { icon: FileSearch, tone: 'bg-teal-100 text-teal-700', title: 'Get your approval roadmap', desc: 'We build a personalised checklist of every approval you need, in the right order.', bullets: ['Only approvals that apply to you', 'Clear order and dependencies', 'Estimated timelines'], you: 'You: review the checklist' },
  { icon: Upload, tone: 'bg-sun/30 text-navy-ink', title: 'Upload documents', desc: 'Documents are validated and cross-checked automatically, so mistakes are caught before you submit.', bullets: ['Instant validation', 'Mismatch and missing-item alerts', 'Reusable business profile'], you: 'You: upload & fix flagged items' },
  { icon: Activity, tone: 'bg-coral/20 text-coral', title: 'Track & stay compliant', desc: 'Monitor applications, respond to queries and never miss a renewal or deadline.', bullets: ['Live application status', 'Query resolution centre', 'Renewal and deadline reminders'], you: 'You: follow the timeline' },
]

export default function HowItWorks() {
  const ref = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start 65%', 'end 55%'] })
  const fade = '[mask-image:linear-gradient(to_bottom,transparent,#000_5%,#000_95%,transparent)]'

  return (
    <section id="how-it-works" className="scroll-mt-16 py-20 sm:py-28">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <ScrollReveal className="mx-auto mb-16 max-w-2xl text-center">
          <div className="eyebrow">How it works</div>
          <h2 className="mt-3 text-3xl font-extrabold tracking-tight text-navy sm:text-4xl">Four clear steps. Always know what’s next.</h2>
          <p className="mt-3 text-gray-600">Each step tells you exactly what to do, so nothing gets missed.</p>
        </ScrollReveal>

        <div ref={ref} className="relative">
          {/* track + scroll-filled progress line (centre on desktop, left on mobile) */}
          <div className={`absolute inset-y-0 left-7 w-0.5 -translate-x-1/2 bg-gray-200 sm:left-1/2 ${fade}`} aria-hidden="true" />
          <motion.div
            className={`absolute inset-y-0 left-7 w-0.5 origin-top -translate-x-1/2 bg-gradient-to-b from-blue-500 via-teal to-coral sm:left-1/2 ${fade}`}
            style={{ scaleY: scrollYProgress }}
            aria-hidden="true"
          />

          <ol className="space-y-10 sm:space-y-14">
            {steps.map((s, i) => {
              const Icon = s.icon
              const right = i % 2 === 1
              return (
                <li key={s.title} className="grid grid-cols-[3.5rem_1fr] items-center gap-x-4 sm:grid-cols-[1fr_5rem_1fr] sm:gap-x-0">
                  {/* node */}
                  <div className="relative z-10 col-start-1 row-start-1 grid justify-self-center sm:col-start-2">
                    <span className="grid h-14 w-14 place-items-center rounded-full border-4 border-cream bg-navy text-xl font-extrabold text-cream shadow-lift">{i + 1}</span>
                  </div>
                  {/* card: alternates left / right on desktop */}
                  <div className={`col-start-2 row-start-1 ${right ? 'sm:col-start-3' : 'sm:col-start-1'}`}>
                    <ScrollReveal x={right ? 44 : -44} y={16}>
                      <div className="group relative overflow-hidden rounded-3xl border border-gray-200 bg-white/90 p-6 shadow-card transition duration-300 hover:-translate-y-1 hover:shadow-lift sm:p-9">
                        <span className="pointer-events-none absolute -right-1 -top-7 select-none text-[9rem] font-black leading-none text-gray-100" aria-hidden="true">{i + 1}</span>
                        <div className="relative">
                          <div className="mb-5 flex items-center gap-4">
                            <span className={`grid h-14 w-14 flex-none place-items-center rounded-2xl ${s.tone}`}><Icon className="h-7 w-7" /></span>
                            <h3 className="text-xl font-extrabold leading-tight text-navy sm:text-2xl">{s.title}</h3>
                          </div>
                          <p className="text-base leading-relaxed text-gray-600">{s.desc}</p>
                          <ul className="mt-5 space-y-2">
                            {s.bullets.map((b) => (
                              <li key={b} className="flex items-center gap-2.5 text-sm font-semibold text-gray-700">
                                <span className="grid h-5 w-5 flex-none place-items-center rounded-full bg-teal-100 text-teal-700"><Check className="h-3 w-3" /></span>{b}
                              </li>
                            ))}
                          </ul>
                          <p className="mt-6 inline-flex rounded-full bg-sun/30 px-4 py-1.5 text-sm font-bold text-navy-ink">{s.you}</p>
                        </div>
                      </div>
                    </ScrollReveal>
                  </div>
                </li>
              )
            })}
          </ol>
        </div>
      </div>
    </section>
  )
}
