'use client'
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion'
import { FileCheck2, ShieldCheck, Lightbulb, Landmark } from 'lucide-react'
import usePrefersReducedMotion from './usePrefersReducedMotion'

/**
 * Pure CSS-3D "approval stack": four glass layers (Idea → Approvals → Documents → Compliance)
 * that tilt with the mouse and float gently. No WebGL, so it is light on low-end phones.
 */
const layers = [
  { label: 'Compliance', icon: ShieldCheck, tone: 'bg-teal text-white' },
  { label: 'Documents', icon: FileCheck2, tone: 'bg-sun text-navy-ink' },
  { label: 'Approvals', icon: Landmark, tone: 'bg-blue-500 text-white' },
  { label: 'Your idea', icon: Lightbulb, tone: 'bg-coral text-white' },
]

export default function IsoStack() {
  const reduced = usePrefersReducedMotion()
  const mx = useMotionValue(0), my = useMotionValue(0)
  const rx = useSpring(useTransform(my, [-1, 1], [62, 50]), { stiffness: 90, damping: 18 })
  const rz = useSpring(useTransform(mx, [-1, 1], [-42, -28]), { stiffness: 90, damping: 18 })

  return (
    <div
      className="relative mx-auto h-[340px] w-full max-w-[460px] sm:h-[420px]"
      style={{ perspective: 1200 }}
      onMouseMove={(e) => {
        if (reduced) return
        const r = e.currentTarget.getBoundingClientRect()
        mx.set(((e.clientX - r.left) / r.width) * 2 - 1)
        my.set(((e.clientY - r.top) / r.height) * 2 - 1)
      }}
      onMouseLeave={() => { mx.set(0); my.set(0) }}
      aria-hidden="true"
    >
      <motion.div
        className="absolute left-1/2 top-1/2 h-[200px] w-[200px] sm:h-[240px] sm:w-[240px]"
        style={{ x: '-50%', y: '-50%', rotateX: reduced ? 56 : rx, rotateZ: reduced ? -35 : rz, transformStyle: 'preserve-3d' }}
      >
        {layers.map((l, i) => {
          const Icon = l.icon
          return (
            <motion.div
              key={l.label}
              className="absolute inset-0 rounded-3xl border border-white/70 bg-white/80 shadow-lift backdrop-blur"
              style={{ transform: `translateZ(${i * 46}px)` }}
              animate={reduced ? undefined : { y: [0, -8, 0] }}
              transition={{ duration: 5 + i * 0.4, repeat: Infinity, ease: 'easeInOut', delay: i * 0.25 }}
            >
              <div className="absolute inset-3 rounded-2xl border border-dashed border-gray-300" />
              <div className={`absolute left-4 top-4 flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-bold shadow-card ${l.tone}`}>
                <Icon className="h-4 w-4" /> {l.label}
              </div>
            </motion.div>
          )
        })}
      </motion.div>
    </div>
  )
}
