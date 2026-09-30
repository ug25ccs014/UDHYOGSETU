'use client'
import { useRef } from 'react'
import { motion, useMotionValue, useSpring } from 'framer-motion'
import usePrefersReducedMotion from './usePrefersReducedMotion'

/** Wrapped element (primary CTA) is pulled gently toward the cursor. Use once per screen. */
export default function Magnet({ children, range = 70, strength = 0.35, className = '' }:
  { children: React.ReactNode; range?: number; strength?: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const reduced = usePrefersReducedMotion()
  const x = useMotionValue(0), y = useMotionValue(0)
  const spring = { stiffness: 200, damping: 16, mass: 0.4 }
  const sx = useSpring(x, spring), sy = useSpring(y, spring)
  if (reduced) return <div className={`inline-block ${className}`}>{children}</div>
  return (
    <motion.div
      ref={ref}
      className={className}
      style={{ x: sx, y: sy, display: 'inline-block' }}
      onMouseMove={(e) => {
        const r = ref.current?.getBoundingClientRect(); if (!r) return
        const dx = e.clientX - (r.left + r.width / 2), dy = e.clientY - (r.top + r.height / 2)
        if (Math.hypot(dx, dy) < range + r.width / 2) { x.set(dx * strength); y.set(dy * strength) } else { x.set(0); y.set(0) }
      }}
      onMouseLeave={() => { x.set(0); y.set(0) }}
    >
      {children}
    </motion.div>
  )
}
