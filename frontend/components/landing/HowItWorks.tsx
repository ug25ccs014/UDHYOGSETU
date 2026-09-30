'use client'

import { useRef } from 'react'
import { motion, useScroll } from 'framer-motion'
import { ClipboardList, FileSearch, Upload, Activity, Check, AlertTriangle } from 'lucide-react'
import ScrollReveal from '@/components/fx/ScrollReveal'

const steps = [
  { icon: ClipboardList, tone: 'bg-blue-100 text-blue-600', title: 'Tell us about your project', desc: 'Answer a few simple questions so we understand what you are setting up.', bullets: ['Sector & unit type', 'Location & investment', 'About 2 minutes'], you: 'You: fill a 2-minute form' },
  { icon: FileSearch, tone: 'bg-teal-100 text-teal-700', title: 'Get your approval roadmap', desc: 'We build a personalised checklist of every approval you need, in the right order.', bullets: ['Only what applies to you', 'Clear order', 'Time estimates'], you: 'You: review the checklist' },
  { icon: Upload, tone: 'bg-sun/30 text-navy-ink', title: 'Upload documents', desc: 'Documents are validated and cross-checked automatically, before you submit.', bullets: ['Instant validation', 'Mismatch alerts', 'Reusable profile'], you: 'You: upload & fix flagged items' },
  { icon: Activity, tone: 'bg-coral/20 text-coral', title: 'Track & stay compliant', desc: 'Monitor applications, answer queries and never miss a renewal or deadline.', bullets: ['Live status', 'Query centre', 'Reminders'], you: 'You: follow the timeline' },
]

/* ---- small "what you will see" previews shown on the opposite side of each card ---- */
const Field = ({ label, value }: { label: string; value: string }) => (
  <div>
    <div className="mb-1 text-[11px] font-bold uppercase tracking-wider text-gray-400">{label}</div>
    <div className="rounded-xl border border-gray-200 bg-white px-3.5 py-2 text-sm font-semibold text-gray-800">{value}</div>
  </div>
)
const File = ({ name, ok, note }: { name: string; ok: boolean; note: string }) => (
  <div className="flex items-center justify-between gap-3 rounded-xl border border-gray-200 bg-white px-3.5 py-2.5 text-sm font-semibold text-gray-800">
    <span className="truncate">{name}</span>
    <span className={`flex flex-none items-center gap-1 text-xs font-bold ${ok ? 'text-teal-700' : 'text-amber-600'}`}>
      {ok ? <Check className="h-3.5 w-3.5" /> : <AlertTriangle className="h-3.5 w-3.5" />} {note}
    </span>
  </div>
)

function Preview({ i }: { i: number }) {
  if (i === 0)
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3"><Field label="Sector" value="Food processing" /><Field label="District" value="Pune" /></div>
        <Field label="Investment" value="₹ 20 Cr" />
        <div className="rounded-full bg-navy py-2.5 text-center text-sm font-bold text-cream">Build my roadmap →</div>
      </div>
    )
  if (i === 1)
    return (
      <ol className="space-y-2.5">
        {[['Factory licence', 'Approved', 'bg-teal text-white'], ['Fire NOC', 'In review', 'bg-blue-500 text-white'], ['Pollution consent', 'Next', 'bg-gray-300 text-gray-700'], ['Labour registration', 'Later', 'bg-gray-200 text-gray-500']].map(([l, st, c], n) => (
          <li key={l} className="flex items-center gap-3">
            <span className={`grid h-7 w-7 flex-none place-items-center rounded-full text-xs font-extrabold ${c}`}>{n + 1}</span>
            <span className="flex-1 rounded-xl border border-gray-200 bg-white px-3.5 py-2 text-sm font-semibold text-gray-800">{l}</span>
            <span className="w-16 text-right text-xs font-bold text-gray-500">{st}</span>
          </li>
        ))}
      </ol>
    )
  if (i === 2)
    return (
      <div className="space-y-2.5">
        <div className="grid place-items-center rounded-2xl border-2 border-dashed border-gray-300 bg-white/70 py-4 text-center">
          <Upload className="mb-1 h-5 w-5 text-blue-500" />
          <div className="text-sm font-bold text-gray-700">Drop files here or browse</div>
        </div>
        <File name="Land deed.pdf" ok note="Verified" />
        <File name="PAN card.pdf" ok={false} note="Name mismatch" />
      </div>
    )
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm font-bold text-gray-800"><span>Application #2041</span><span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs text-blue-700">Under review</span></div>
      <div className="flex items-center gap-1.5 text-[11px] font-bold text-gray-500">
        {['Submitted', 'Review', 'Query', 'Approved'].map((t, n) => (
          <div key={t} className="flex-1"><div className={`mb-1 h-1.5 rounded-full ${n < 2 ? 'bg-gradient-to-r from-blue-500 to-teal' : 'bg-gray-200'}`} />{t}</div>
        ))}
      </div>
      <div>
        <div className="mb-1 flex justify-between text-xs font-bold text-gray-500"><span>Fire NOC renewal</span><span>12 days</span></div>
        <div className="h-2 overflow-hidden rounded-full bg-gray-200"><div className="h-full w-4/5 rounded-full bg-coral" /></div>
      </div>
    </div>
  )
}

export default function HowItWorks() {
  const ref = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start 65%', 'end 55%'] })
  const fade = '[mask-image:linear-gradient(to_bottom,transparent,#000_5%,#000_95%,transparent)]'

  return (
    <section id="how-it-works" className="scroll-mt-20 py-16 sm:py-24">
      <div className="mx-auto max-w-7xl px-5 sm:px-8 lg:px-14">
        <ScrollReveal className="mx-auto mb-14 max-w-2xl text-center">
          <div className="eyebrow">How it works</div>
          <h2 className="mt-3 text-3xl font-extrabold tracking-tight text-navy sm:text-4xl">Four clear steps. Always know what’s next.</h2>
          <p className="mt-3 text-gray-600">Each step tells you exactly what to do, so nothing gets missed.</p>
        </ScrollReveal>

        <div ref={ref} className="relative">
          <div className={`absolute inset-y-0 left-7 w-0.5 -translate-x-1/2 bg-gray-200 sm:left-1/2 ${fade}`} aria-hidden="true" />
          <motion.div
            className={`absolute inset-y-0 left-7 w-0.5 origin-top -translate-x-1/2 bg-gradient-to-b from-blue-500 via-teal to-coral sm:left-1/2 ${fade}`}
            style={{ scaleY: scrollYProgress }}
            aria-hidden="true"
          />

          <ol className="space-y-8 sm:space-y-10">
            {steps.map((s, i) => {
              const Icon = s.icon
              const right = i % 2 === 1
              return (
                <li key={s.title} className="grid grid-cols-[3.5rem_1fr] items-center gap-x-4 sm:grid-cols-[1fr_4.5rem_1fr] sm:gap-x-0">
                  <div className="relative z-10 col-start-1 row-start-1 grid justify-self-center sm:col-start-2">
                    <span className="grid h-12 w-12 place-items-center rounded-full border-4 border-cream bg-navy text-lg font-extrabold text-cream shadow-lift">{i + 1}</span>
                  </div>

                  {/* rectangular step card */}
                  <div className={`col-start-2 row-start-1 ${right ? 'sm:col-start-3 sm:pl-6' : 'sm:col-start-1 sm:pr-6'}`}>
                    <ScrollReveal x={right ? 40 : -40} y={12}>
                      <div className="relative overflow-hidden rounded-2xl border border-gray-200 bg-white/90 p-5 shadow-card transition duration-300 hover:-translate-y-0.5 hover:shadow-lift sm:p-6">
                        <span className="pointer-events-none absolute -top-3 right-4 select-none text-7xl font-black leading-none text-gray-100" aria-hidden="true">{i + 1}</span>
                        <div className="relative flex items-start gap-4">
                          <span className={`grid h-12 w-12 flex-none place-items-center rounded-xl ${s.tone}`}><Icon className="h-6 w-6" /></span>
                          <div className="min-w-0">
                            <h3 className="text-lg font-extrabold leading-tight text-navy sm:text-xl">{s.title}</h3>
                            <p className="mt-1 text-sm leading-relaxed text-gray-600">{s.desc}</p>
                          </div>
                        </div>
                        <div className="relative mt-4 flex flex-wrap items-center gap-2">
                          {s.bullets.map((b) => (
                            <span key={b} className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-xs font-semibold text-gray-700">
                              <Check className="h-3 w-3 text-teal-700" />{b}
                            </span>
                          ))}
                          <span className="rounded-full bg-sun/30 px-3 py-1 text-xs font-bold text-navy-ink">{s.you}</span>
                        </div>
                      </div>
                    </ScrollReveal>
                  </div>

                  {/* preview fills the opposite side (desktop) */}
                  <div className={`hidden row-start-1 sm:block ${right ? 'sm:col-start-1 sm:pr-6' : 'sm:col-start-3 sm:pl-6'}`}>
                    <ScrollReveal x={right ? -40 : 40} y={12} delay={0.1}>
                      <div className="rounded-2xl border border-gray-200 bg-white/55 p-5 shadow-card backdrop-blur">
                        <div className="mb-3 text-[11px] font-extrabold uppercase tracking-[.16em] text-gray-400">What you’ll see</div>
                        <Preview i={i} />
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
