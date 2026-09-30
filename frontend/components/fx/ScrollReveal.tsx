'use client'
import { motion } from 'framer-motion'
import usePrefersReducedMotion from './usePrefersReducedMotion'

/** Fade + rise into place when scrolled into view (runs once). */
export default function ScrollReveal({
  children, y = 26, delay = 0, duration = 0.6, className = '',
}: { children: React.ReactNode; y?: number; delay?: number; duration?: number; className?: string }) {
  const reduced = usePrefersReducedMotion()
  return (
    <motion.div
      className={className}
      initial={reduced ? false : { opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: reduced ? 0 : duration, delay: reduced ? 0 : delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  )
}
