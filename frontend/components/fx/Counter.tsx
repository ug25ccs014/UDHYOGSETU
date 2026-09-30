'use client'
import { useEffect, useRef, useState } from 'react'
import { useInView } from 'framer-motion'

/** Counts 0 → value when scrolled into view. */
export default function Counter({ value, suffix = '', prefix = '', durationMs = 1400 }:
  { value: number; suffix?: string; prefix?: string; durationMs?: number }) {
  const ref = useRef<HTMLSpanElement>(null)
  const inView = useInView(ref, { once: true, margin: '-80px' })
  const [n, setN] = useState(0)
  useEffect(() => {
    if (!inView) return
    let raf = 0; const t0 = performance.now()
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / durationMs)
      setN(Math.round((1 - Math.pow(1 - p, 3)) * value))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [inView, value, durationMs])
  return <span ref={ref}>{prefix}{n.toLocaleString()}{suffix}</span>
}
