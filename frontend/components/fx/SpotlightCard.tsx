'use client'
import { useRef } from 'react'

/** Glass card with a cursor-following glow (styles live in globals.css). */
export default function SpotlightCard({ children, className = '', color = 'rgba(63,127,214,.16)' }:
  { children: React.ReactNode; className?: string; color?: string }) {
  const ref = useRef<HTMLDivElement>(null)
  return (
    <div
      ref={ref}
      className={`spotlight-card ${className}`}
      style={{ ['--spotlight-color' as any]: color }}
      onMouseMove={(e) => {
        const r = ref.current?.getBoundingClientRect(); if (!r) return
        ref.current!.style.setProperty('--sx', `${e.clientX - r.left}px`)
        ref.current!.style.setProperty('--sy', `${e.clientY - r.top}px`)
      }}
    >
      <div className="spotlight-card-glow" aria-hidden="true" />
      <div className="spotlight-card-body">{children}</div>
    </div>
  )
}
