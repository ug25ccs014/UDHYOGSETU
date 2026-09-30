'use client'

import { useEffect, useRef, useState } from 'react'
import { Check, ChevronDown, Globe } from 'lucide-react'
import { cn } from '@/lib/utils'
import { LANGUAGES, useLanguage } from '@/lib/language'

/**
 * Compact language selector: globe + current language + chevron.
 * `tone="dark"` is for the navy landing navbar; `tone="light"` for auth and dashboard.
 */
export default function LanguageSwitcher({
  tone = 'light',
  className,
  iconOnlyOnMobile = false,
}: {
  tone?: 'light' | 'dark'
  className?: string
  iconOnlyOnMobile?: boolean
}) {
  const { language, setLanguage, t } = useLanguage()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const current = LANGUAGES.find((l) => l.code === language) ?? LANGUAGES[0]

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent | TouchEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', onDown)
    document.addEventListener('touchstart', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('touchstart', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div ref={ref} className={cn('relative', className)}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`${t('lang.select')}: ${current.label}`}
        className={cn(
          'inline-flex h-8 items-center gap-1.5 rounded-full border px-2.5 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
          tone === 'dark'
            ? 'border-white/30 bg-white/10 text-cream hover:border-white/50 hover:bg-white/20'
            : 'border-gray-300 bg-white/70 text-navy hover:border-blue-300 hover:bg-white',
        )}
      >
        <Globe className="h-4 w-4 flex-none" aria-hidden="true" />
        <span className={cn('whitespace-nowrap', iconOnlyOnMobile && 'hidden sm:inline')}>{current.label}</span>
        <ChevronDown className={cn('h-3.5 w-3.5 flex-none transition-transform', open && 'rotate-180')} aria-hidden="true" />
      </button>
      {open && (
        <ul
          role="listbox"
          aria-label={t('lang.select')}
          className="absolute right-0 z-[60] mt-2 min-w-[9rem] overflow-hidden rounded-xl border border-gray-200 bg-white py-1 shadow-xl"
        >
          {LANGUAGES.map((l) => (
            <li key={l.code} role="option" aria-selected={l.code === language}>
              <button
                type="button"
                lang={l.code}
                onClick={() => {
                  setLanguage(l.code)
                  setOpen(false)
                }}
                className={cn(
                  'flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm font-semibold text-gray-800 hover:bg-gray-100',
                  l.code === language && 'text-navy',
                )}
              >
                {l.label}
                {l.code === language && <Check className="h-4 w-4 text-teal-700" aria-hidden="true" />}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
