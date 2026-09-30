'use client'

import React, { useEffect, useRef, useState } from 'react'
import { Bot, Loader2, MessageCircle, Send, Sparkles, Trash2, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useRegulatoryQuery } from '@/hooks/useApi'
import { useLanguage, TKey } from '@/lib/language'

interface ChatMessage {
  id: string
  type: 'user' | 'assistant'
  content: string
  sources?: Array<{ title: string; url?: string }>
}

interface CopilotDrawerProps {
  /** Current project id (if the user is inside a project) so answers get project context. */
  projectId?: string
}

const suggestedQuestionKeys: TKey[] = ['copilot.q1', 'copilot.q2', 'copilot.q3', 'copilot.q4']

export default function CopilotDrawer({ projectId }: CopilotDrawerProps) {
  const { t } = useLanguage()
  const suggestedQuestions = suggestedQuestionKeys.map((k) => t(k))
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const endRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const regQuery = useRegulatoryQuery()

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open, regQuery.isPending])

  // Close on Escape, focus the input when opened.
  useEffect(() => {
    if (!open) return
    inputRef.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  const send = async (raw: string) => {
    const question = raw.trim()
    if (!question || regQuery.isPending) return

    setMessages((prev) => [...prev, { id: `u-${Date.now()}`, type: 'user', content: question }])
    setInput('')

    try {
      const data = await regQuery.mutateAsync({ question, projectId })
      setMessages((prev) => [
        ...prev,
        { id: `a-${Date.now()}`, type: 'assistant', content: data.answer, sources: data.sources },
      ])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `e-${Date.now()}`,
          type: 'assistant',
          content: t('copilot.error'),
        },
      ])
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    send(input)
  }

  return (
    <>
      {/* Floating launcher */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={t('copilot.open')}
        aria-expanded={open}
        className={cn(
          'fixed bottom-5 right-5 z-40 grid h-14 w-14 place-items-center rounded-full bg-navy text-cream shadow-lift ring-4 ring-cream/70 transition-all duration-200 hover:scale-105 hover:bg-navy-2 focus-visible:outline-none focus-visible:ring-sun',
          open && 'pointer-events-none scale-75 opacity-0',
        )}
      >
        <MessageCircle className="h-6 w-6" />
        <span className="absolute -right-0.5 -top-0.5 grid h-5 w-5 place-items-center rounded-full bg-sun text-navy">
          <Sparkles className="h-3 w-3" />
        </span>
      </button>

      {/* Backdrop (mobile only) */}
      {open && (
        <div
          className="fixed inset-0 z-[60] bg-black/40 sm:hidden"
          onClick={() => setOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Right-side drawer */}
      <aside
        role="dialog"
        aria-label={t('copilot.title')}
        aria-hidden={!open}
        className={cn(
          'fixed inset-y-0 right-0 z-[70] flex w-full flex-col border-l border-gray-200 bg-white shadow-lift transition-transform duration-300 ease-out sm:w-[400px]',
          open ? 'translate-x-0' : 'pointer-events-none translate-x-full',
        )}
      >
        {/* Header */}
        <div className="flex h-16 flex-none items-center justify-between border-b border-gray-200 bg-navy px-4 text-cream">
          <div className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-full bg-white/10">
              <Bot className="h-5 w-5 text-sun" />
            </span>
            <div className="leading-tight">
              <p className="text-sm font-bold">{t('copilot.title')}</p>
              <p className="text-[11px] text-cream/70">
                {projectId ? t('copilot.ctxProject') : t('copilot.ctxGeneral')}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {messages.length > 0 && (
              <button
                type="button"
                onClick={() => setMessages([])}
                aria-label={t('copilot.clear')}
                title={t('copilot.clear')}
                className="grid h-9 w-9 place-items-center rounded-xl text-cream/80 hover:bg-white/10"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label={t('copilot.close')}
              className="grid h-9 w-9 place-items-center rounded-xl text-cream/80 hover:bg-white/10"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 space-y-4 overflow-y-auto bg-cream/40 p-4">
          {messages.length === 0 ? (
            <div className="space-y-5 pt-4">
              <div className="text-center">
                <div className="mx-auto mb-3 grid h-14 w-14 place-items-center rounded-2xl bg-navy/10">
                  <Sparkles className="h-7 w-7 text-navy" />
                </div>
                <h2 className="text-lg font-bold text-navy">{t('copilot.helpTitle')}</h2>
                <p className="mt-1 text-sm text-gray-600">{t('copilot.helpSub')}</p>
              </div>
              <div className="space-y-2">
                {suggestedQuestions.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => send(q)}
                    className="w-full rounded-xl border border-gray-200 bg-white p-3 text-left text-sm text-gray-700 transition hover:border-navy/40 hover:bg-white hover:shadow-card"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m) => (
              <div key={m.id} className={cn('flex', m.type === 'user' ? 'justify-end' : 'justify-start')}>
                <div
                  className={cn(
                    'max-w-[88%] rounded-2xl px-4 py-2.5 text-sm',
                    m.type === 'user'
                      ? 'rounded-br-md bg-navy text-cream'
                      : 'rounded-bl-md border border-gray-200 bg-white text-gray-900',
                  )}
                >
                  <p className="whitespace-pre-wrap">{m.content}</p>
                  {m.sources && m.sources.length > 0 && (
                    <div className="mt-2 space-y-0.5 border-t border-gray-100 pt-2 text-xs text-gray-500">
                      <p className="font-semibold">{t('copilot.sources')}</p>
                      {m.sources.map((s, i) =>
                        s.url ? (
                          <a
                            key={i}
                            href={s.url}
                            target="_blank"
                            rel="noreferrer"
                            className="block truncate text-navy underline-offset-2 hover:underline"
                          >
                            {s.title}
                          </a>
                        ) : (
                          <p key={i} className="truncate">{s.title}</p>
                        ),
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}

          {regQuery.isPending && (
            <div className="flex justify-start">
              <div className="rounded-2xl rounded-bl-md border border-gray-200 bg-white px-4 py-3">
                <div className="flex space-x-1.5">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:150ms]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:300ms]" />
                </div>
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        {/* Input */}
        <form onSubmit={handleSubmit} className="flex-none border-t border-gray-200 bg-white p-3">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              aria-label={t('copilot.askLabel')}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={t('copilot.phDrawer')}
              disabled={regQuery.isPending}
              className="min-w-0 flex-1 rounded-xl border border-gray-300 px-4 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-navy"
            />
            <button
              type="submit"
              aria-label={t('copilot.sendLabel')}
              disabled={regQuery.isPending || !input.trim()}
              className="grid h-11 w-11 flex-none place-items-center rounded-xl bg-navy text-cream transition hover:bg-navy-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {regQuery.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </button>
          </div>
        </form>
      </aside>
    </>
  )
}
