'use client'
import React from 'react'
import { motion } from 'framer-motion'
import usePrefersReducedMotion from './usePrefersReducedMotion'

type Segment = { text: string; gradient?: boolean }

/** Word-by-word blur + rise reveal. Pass `segments` so a few words can be gradient. */
export default function BlurText({
  segments, as: Tag = 'h1', className = '', delay = 0, staggerMs = 45,
}: { segments: Segment[]; as?: any; className?: string; delay?: number; staggerMs?: number }) {
  const reduced = usePrefersReducedMotion()
  let n = 0
  return (
    <Tag className={className}>
      {segments.map((seg, si) => {
        const words = seg.text.split(' ')
        return (
          <React.Fragment key={si}>
            {words.map((w, wi) => {
              const i = n++
              return (
                <motion.span
                  key={wi}
                  className={seg.gradient ? 'grad-text grad-text-animate' : undefined}
                  initial={reduced ? false : { opacity: 0, filter: 'blur(10px)', y: 16 }}
                  animate={{ opacity: 1, filter: 'blur(0px)', y: 0 }}
                  transition={{ duration: reduced ? 0 : 0.6, ease: [0.22, 1, 0.36, 1], delay: reduced ? 0 : delay + (i * staggerMs) / 1000 }}
                  style={{ display: 'inline-block' }}
                >
                  {w}{wi < words.length - 1 ? '\u00A0' : ''}
                </motion.span>
              )
            })}
            {si < segments.length - 1 ? ' ' : ''}
          </React.Fragment>
        )
      })}
    </Tag>
  )
}
