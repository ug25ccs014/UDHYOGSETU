'use client'

import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { FileSearch, ShieldCheck, Landmark, Bot, Gift, Check, AlertTriangle } from 'lucide-react'
import usePrefersReducedMotion from './usePrefersReducedMotion'

/**
 * Hero visual: 5 floating glass panes in a tilted 3D stack.
 * Hover (or tap) a pane -> it turns to face you, grows, and shows a mini preview of that feature.
 * Hit-testing is done on the container (not the tilted panes) so the hover never flickers.
 */
const N = 5, S = 100, TOP = 40, CH = TOP * 2 + S * N, CW = 560, PW = 460, PH = 250, FLAT = 1.12
const center = (i: number) => TOP + S * i + S / 2
const flatCenter = (i: number) => Math.min(Math.max(center(i), (PH * FLAT) / 2 + 8), CH - (PH * FLAT) / 2 - 8)

function pick(x: number, y: number, active: number | null): number | null {
  if (active !== null && Math.abs(y - flatCenter(active)) <= (PH * FLAT) / 2 && Math.abs(x - CW / 2) <= (PW * FLAT) / 2) return active
  if (x < 6 || x > CW - 6 || y < TOP || y > TOP + S * N) return null
  return Math.min(N - 1, Math.floor((y - TOP) / S))
}

const Row = ({ children, tone = '#2F9C84', label }: { children?: React.ReactNode; tone?: string; label: string }) => (
  <div className="flex items-center justify-between gap-2 rounded-lg bg-white/90 px-3 py-2 text-xs font-semibold text-gray-800 shadow-sm">
    <span className="truncate">{label}</span>
    <span className="flex flex-none items-center gap-1" style={{ color: tone }}>{children}</span>
  </div>
)

const arts: Record<string, React.ReactNode> = {
  approvals: (
    <div className="space-y-2">
      <Row label="Factory licence" tone="#2F9C84">● Approved</Row>
      <Row label="Fire NOC" tone="#C98F00">● In review</Row>
      <Row label="Pollution consent" tone="#93A0AB">● To start</Row>
      <div className="h-1.5 overflow-hidden rounded-full bg-gray-200"><div className="h-full w-2/5 rounded-full bg-blue-500" /></div>
    </div>
  ),
  docs: (
    <div className="space-y-2">
      <Row label="Land documents" tone="#2F9C84"><Check className="h-3 w-3" /> Verified</Row>
      <Row label="Address on PAN vs deed" tone="#C98F00"><AlertTriangle className="h-3 w-3" /> Mismatch</Row>
      <Row label="Project report" tone="#2F9C84"><Check className="h-3 w-3" /> Verified</Row>
    </div>
  ),
  compliance: (
    <div className="space-y-2.5">
      {[['Fire NOC renewal', '12 days', 'w-4/5', 'bg-coral'], ['Pollution returns', '30 days', 'w-3/5', 'bg-sun'], ['Labour filing', '58 days', 'w-2/5', 'bg-teal']].map(([l, d, w, c]) => (
        <div key={l}>
          <div className="mb-1 flex justify-between text-xs font-semibold text-gray-800"><span>{l}</span><span className="text-gray-500">{d}</span></div>
          <div className="h-1.5 overflow-hidden rounded-full bg-gray-200"><div className={`h-full rounded-full ${w} ${c}`} /></div>
        </div>
      ))}
    </div>
  ),
  copilot: (
    <div className="space-y-2 text-xs font-semibold">
      <div className="ml-auto w-fit max-w-[85%] rounded-xl rounded-br-sm bg-navy px-3 py-2 text-cream">Which approvals does my unit need?</div>
      <div className="w-fit max-w-[90%] rounded-xl rounded-bl-sm bg-white/90 px-3 py-2 text-gray-800 shadow-sm">4 approvals apply. Start with the factory licence.</div>
    </div>
  ),
  schemes: (
    <div className="space-y-2">
      <Row label="Capital subsidy" tone="#2F9C84">Eligible</Row>
      <Row label="Interest subvention" tone="#2F9C84">Eligible</Row>
      <Row label="Stamp duty waiver" tone="#C98F00">Check</Row>
    </div>
  ),
}

const cards = [
  { key: 'approvals', title: 'Intelligent Approvals', tag: 'Roadmap', desc: 'A personalised checklist of every approval your unit needs, in the right order.', icon: FileSearch, accent: '#3F7FD6', ink: '#fff' },
  { key: 'docs', title: 'Document Intelligence', tag: 'Validation', desc: 'Upload once. Documents are validated and cross-checked before you submit.', icon: ShieldCheck, accent: '#2F9C84', ink: '#fff' },
  { key: 'compliance', title: 'Compliance Tracking', tag: 'Deadlines', desc: 'Never miss a renewal, return or filing after you get approved.', icon: Landmark, accent: '#F2C94C', ink: '#102A43' },
  { key: 'copilot', title: 'Regulatory Copilot', tag: 'Ask anything', desc: 'Ask about regulations and get clear, grounded answers.', icon: Bot, accent: '#F07C61', ink: '#fff' },
  { key: 'schemes', title: 'Incentive Discovery', tag: 'Schemes', desc: 'Find government schemes you qualify for and apply in one place.', icon: Gift, accent: '#173A59', ink: '#FFFFE3' },
]

export default function GlassStack() {
  const reduced = usePrefersReducedMotion()
  const outer = useRef<HTMLDivElement>(null)
  const box = useRef<HTMLDivElement>(null)
  const [active, setActive] = useState<number | null>(null)
  const [k, setK] = useState(1) // fit-to-width scale

  useEffect(() => {
    const el = outer.current
    if (!el) return
    // fit to column width AND to the visible viewport height so the whole stack is always on screen
    const fit = () => {
      const byW = el.clientWidth / CW
      const byH = window.innerWidth >= 1024 ? Math.max(0.6, (window.innerHeight - 68 - 64) / CH) : 1
      setK(Math.min(1, byW, byH))
    }
    fit()
    const ro = new ResizeObserver(fit)
    ro.observe(el)
    window.addEventListener('resize', fit)
    return () => { ro.disconnect(); window.removeEventListener('resize', fit) }
  }, [])

  const local = (e: React.PointerEvent) => {
    const r = box.current!.getBoundingClientRect()
    const sc = r.height / CH
    return { x: (e.clientX - r.left) / sc, y: (e.clientY - r.top) / sc }
  }

  return (
    <div ref={outer} className="relative mx-auto w-full lg:translate-x-4" style={{ height: CH * k }} aria-hidden="true">
      <div
        ref={box}
        className="absolute left-1/2 top-0"
        style={{ width: CW, height: CH, marginLeft: -CW / 2, transform: `scale(${k})`, transformOrigin: 'top center', touchAction: 'pan-y' }}
        onPointerMove={(e) => { if (e.pointerType !== 'mouse') return; const { x, y } = local(e); setActive((a) => pick(x, y, a)) }}
        onPointerLeave={(e) => { if (e.pointerType === 'mouse') setActive(null) }}
        onPointerDown={(e) => { if (e.pointerType === 'mouse') return; const { x, y } = local(e); setActive((a) => pick(x, y, a)) }}
      >
        {cards.map((c, i) => {
          const isActive = active === i
          const dim = active !== null && !isActive
          const Icon = c.icon
          return (
            <div
              key={c.key}
              className={`absolute ${active === null && !reduced ? 'animate-floaty' : ''}`}
              style={{ left: (CW - PW) / 2, top: center(i) - PH / 2, width: PW, height: PH, zIndex: isActive ? 50 : i, animationDelay: `${i * -1.1}s`, pointerEvents: 'none' }}
            >
              <motion.div
                className="relative h-full w-full overflow-hidden rounded-3xl border"
                style={{
                  transformPerspective: 1400,
                  borderColor: 'rgba(255,255,255,.95)',
                  background: `linear-gradient(145deg, rgba(255,255,255,.92), rgba(255,255,255,.6) 55%, ${c.accent}26)`,
                  boxShadow: isActive ? '0 30px 60px rgba(23,58,89,.22)' : '0 16px 34px rgba(23,58,89,.12)',
                  backdropFilter: 'blur(10px)',
                }}
                animate={{
                  rotateX: isActive ? 0 : 58,
                  rotateZ: isActive ? 0 : -28,
                  scale: isActive ? FLAT : 1,
                  y: isActive ? flatCenter(i) - center(i) : 0,
                  opacity: dim ? 0.35 : 1,
                }}
                transition={reduced ? { duration: 0 } : { type: 'spring', stiffness: 170, damping: 22 }}
              >
                {/* Collapsed face */}
                <div className="absolute inset-0 p-7 transition-opacity duration-200" style={{ opacity: isActive ? 0 : 1 }}>
                  <div className="flex items-center gap-3">
                    <span className="grid h-14 w-14 place-items-center rounded-2xl shadow-card" style={{ background: c.accent, color: c.ink }}><Icon className="h-7 w-7" /></span>
                    <div className="min-w-0">
                      <div className="truncate text-2xl font-extrabold leading-tight text-navy">{c.title}</div>
                      <div className="text-xs font-bold uppercase tracking-widest text-gray-500">{c.tag}</div>
                    </div>
                  </div>
                  <div className="mt-7 space-y-3">
                    <div className="h-3 w-4/5 rounded-full bg-gray-200/80" />
                    <div className="h-3 w-3/5 rounded-full bg-gray-200/80" />
                    <div className="h-3 w-2/5 rounded-full" style={{ background: `${c.accent}55` }} />
                  </div>
                  <span className="absolute bottom-4 right-7 text-4xl font-black text-gray-200">0{i + 1}</span>
                </div>
                {/* Detail face (visible when the pane faces you) */}
                <div className="absolute inset-0 flex flex-col p-4 transition-opacity duration-200" style={{ opacity: isActive ? 1 : 0 }}>
                  <div className="flex items-center gap-2">
                    <span className="grid h-8 w-8 place-items-center rounded-lg" style={{ background: c.accent, color: c.ink }}><Icon className="h-4 w-4" /></span>
                    <span className="text-base font-extrabold text-navy">{c.title}</span>
                  </div>
                  <p className="mt-2 text-xs leading-snug text-gray-600">{c.desc}</p>
                  <div className="mt-auto pt-2">{arts[c.key]}</div>
                </div>
              </motion.div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
