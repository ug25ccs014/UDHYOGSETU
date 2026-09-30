'use client'
import { motion } from 'framer-motion'
import usePrefersReducedMotion from './usePrefersReducedMotion'

/** Fade + rise into place when scrolled into view (runs once). */
export default function ScrollReveal({
  children, y = 26, x = 0, delay = 0, duration = 0.6, className = '',
}: { children: React.ReactNode; y?: number; x?: number; delay?: number; duration?: number; className?: string }) {
  const reduced = usePrefersReducedMotion()
  return (
    <motion.div
      className={className}
      initial={reduced ? false : { opacity: 0, x, y }}
      whileInView={{ opacity: 1, x: 0, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: reduced ? 0 : duration, delay: reduced ? 0 : delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  )
}
