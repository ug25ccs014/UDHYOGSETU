'use client'

import { createContext, useCallback, useContext, useEffect, useMemo, useState, ReactNode } from 'react'
import en, { Translations } from '@/locales/en'
import hi from '@/locales/hi'
import mr from '@/locales/mr'

export type Language = 'en' | 'hi' | 'mr'

export const LANGUAGE_STORAGE_KEY = 'udyogsetu_language'
export const DEFAULT_LANGUAGE: Language = 'en'

/** Native names are shown as-is in the selector (never translated). */
export const LANGUAGES: { code: Language; label: string; locale: string }[] = [
  { code: 'en', label: 'English', locale: 'en-IN' },
  { code: 'hi', label: 'हिन्दी', locale: 'hi-IN' },
  { code: 'mr', label: 'मराठी', locale: 'mr-IN' },
]

const dictionaries: Record<Language, Translations> = { en, hi, mr }

type Paths<T> = T extends string
  ? never
  : { [K in keyof T & string]: T[K] extends string ? K : `${K}.${Paths<T[K]>}` }[keyof T & string]
export type TKey = Paths<Translations>

export function isLanguage(value: unknown): value is Language {
  return value === 'en' || value === 'hi' || value === 'mr'
}

function lookup(dict: unknown, key: string): string | undefined {
  const found = key.split('.').reduce<any>((node, part) => (node == null ? undefined : node[part]), dict)
  return typeof found === 'string' ? found : undefined
}

function interpolate(text: string, vars?: Record<string, string | number>) {
  if (!vars) return text
  return text.replace(/\{(\w+)\}/g, (_, name) => (name in vars ? String(vars[name]) : `{${name}}`))
}

/** Pure translate function (usable outside React, e.g. in tests). */
export function translate(language: Language, key: TKey, vars?: Record<string, string | number>): string {
  return interpolate(lookup(dictionaries[language], key) ?? lookup(en, key) ?? key, vars)
}

type LanguageContextValue = {
  language: Language
  locale: string
  setLanguage: (language: Language) => void
  t: (key: TKey, vars?: Record<string, string | number>) => string
  /** Display label for a backend enum value (e.g. APPROVED). The raw value is never changed. */
  statusLabel: (value?: string | null) => string
  formatDate: (value: string | number | Date | null | undefined, options?: Intl.DateTimeFormatOptions) => string
  formatNumber: (value: number, options?: Intl.NumberFormatOptions) => string
  /** Currency always stays INR / ₹. */
  formatCurrency: (value: number, options?: Intl.NumberFormatOptions) => string
}

const LanguageContext = createContext<LanguageContextValue | null>(null)

export function LanguageProvider({ children }: { children: ReactNode }) {
  // Always start with the default so server and first client render match (no hydration mismatch);
  // the saved preference is applied right after mount.
  const [language, setLanguageState] = useState<Language>(DEFAULT_LANGUAGE)

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(LANGUAGE_STORAGE_KEY)
      if (isLanguage(saved)) setLanguageState(saved)
    } catch {
      /* storage unavailable — stay on default */
    }
  }, [])

  const locale = LANGUAGES.find((l) => l.code === language)?.locale ?? 'en-IN'

  useEffect(() => {
    document.documentElement.lang = locale
  }, [locale])

  const setLanguage = useCallback((next: Language) => {
    setLanguageState(next)
    try {
      window.localStorage.setItem(LANGUAGE_STORAGE_KEY, next)
    } catch {
      /* ignore */
    }
  }, [])

  const value = useMemo<LanguageContextValue>(() => {
    const t: LanguageContextValue['t'] = (key, vars) => translate(language, key, vars)
    const statusLabel = (raw?: string | null) => {
      if (!raw) return ''
      const hit = lookup(dictionaries[language].status, raw) ?? lookup(en.status, raw)
      if (hit) return hit
      const pretty = raw.replace(/_/g, ' ').toLowerCase()
      return pretty.charAt(0).toUpperCase() + pretty.slice(1)
    }
    const formatDate: LanguageContextValue['formatDate'] = (v, options) => {
      if (v == null || v === '') return ''
      const d = v instanceof Date ? v : new Date(v)
      return Number.isNaN(d.getTime()) ? String(v) : new Intl.DateTimeFormat(locale, options ?? { dateStyle: 'medium' }).format(d)
    }
    const formatNumber: LanguageContextValue['formatNumber'] = (v, options) => new Intl.NumberFormat(locale, options).format(v)
    const formatCurrency: LanguageContextValue['formatCurrency'] = (v, options) =>
      new Intl.NumberFormat(locale, { style: 'currency', currency: 'INR', maximumFractionDigits: 0, ...options }).format(v)
    return { language, locale, setLanguage, t, statusLabel, formatDate, formatNumber, formatCurrency }
  }, [language, locale, setLanguage])

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext)
  if (!ctx) throw new Error('useLanguage must be used inside <LanguageProvider>')
  return ctx
}
