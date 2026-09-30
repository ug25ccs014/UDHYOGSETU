'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useRegulatoryQuery } from '@/hooks/useApi'
import { useLanguage, TKey } from '@/lib/language'

interface ChatMessage {
  id: string
  type: 'user' | 'assistant'
  content: string
  timestamp: Date
  sources?: Array<{ title: string; url: string }>
}

interface RegulatoryCourtilotProps {
  projectId: string
}

export function RegulatoryCourtilot({ projectId }: RegulatoryCourtilotProps) {
  const { t, locale } = useLanguage()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [showSourcesPanel, setShowSourcesPanel] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const regQuery = useRegulatoryQuery()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: input,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')

    try {
      const data = await regQuery.mutateAsync({ question: input, projectId })

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: data.answer,
        timestamp: new Date(),
        sources: data.sources,
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: t('copilot.error'),
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    }
  }

  const suggestedQuestions = (['copilot.q1', 'copilot.q2', 'copilot.q3', 'copilot.q4', 'copilot.q5'] as TKey[]).map((k) => t(k))

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4 lg:h-[620px]">
      {/* Chat Panel */}
      <div className="flex flex-col border border-gray-200 rounded-xl overflow-hidden bg-white h-[65vh] max-h-[620px] lg:h-auto">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="space-y-6">
              <div className="text-center pt-8">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-50 mb-4">
                  <Sparkles className="w-8 h-8 text-blue-600" />
                </div>
                <h2 className="text-2xl font-bold text-gray-900">{t('copilot.title')}</h2>
                <p className="text-gray-600 mt-2">{t('copilot.pageSub')}</p>
              </div>

              <div className="grid grid-cols-1 gap-2 max-w-lg mx-auto">
                {suggestedQuestions.map((question, idx) => (
                  <button
                    key={idx}
                    onClick={() => setInput(question)}
                    className="text-left p-3 border border-gray-200 rounded-xl hover:bg-gray-50 hover:border-blue-300 transition"
                  >
                    <p className="text-sm text-gray-700">{question}</p>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((message, idx) => (
              <div
                key={idx}
                className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] px-4 py-3 rounded-xl ${
                    message.type === 'user'
                      ? 'bg-blue-600 text-white rounded-br-none'
                      : 'bg-gray-100 text-gray-900 rounded-bl-none'
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  {message.sources && message.sources.length > 0 && (
                    <div className="mt-2 text-xs opacity-75">
                      <p className="font-semibold">{t('copilot.sourcesColon')}</p>
                      {message.sources.map((source, i) => (
                        <p key={i} className="truncate">{source.title}</p>
                      ))}
                    </div>
                  )}
                  <p className="text-xs opacity-60 mt-1">
                    {message.timestamp.toLocaleTimeString(locale)}
                  </p>
                </div>
              </div>
            ))
          )}
          {regQuery.isPending && (
            <div className="flex justify-start">
              <div className="bg-gray-100 px-4 py-3 rounded-xl rounded-bl-none">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200"></div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <form onSubmit={handleSubmit} className="border-t border-gray-200 p-4 bg-gray-50">
          <div className="flex gap-2">
            <input
              type="text"
              aria-label={t('copilot.askLabel')}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={t('copilot.phPage')}
              className="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={regQuery.isPending}
            />
            <Button type="submit" aria-label={t('copilot.sendLabel')} disabled={regQuery.isPending || !input.trim()}>
              {regQuery.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  {t('copilot.send')}
                </>
              )}
            </Button>
          </div>
        </form>
      </div>

      {/* Sources Panel */}
      <div className="flex flex-col border border-gray-200 rounded-xl overflow-hidden bg-white max-h-80 lg:max-h-none">
        <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
          <h3 className="font-semibold text-gray-900">{t('copilot.panelTitle')}</h3>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages
            .filter(m => m.type === 'assistant' && m.sources)
            .flatMap(m => m.sources || [])
            .reduce((unique, item, idx, arr) => {
              if (!unique.find((i: any) => i.title === item.title)) {
                unique.push(item)
              }
              return unique
                        }, [] as any[])
            .map((source: any, idx: number) => (
              <div key={idx} className="p-3 border border-gray-200 rounded-xl hover:shadow-md transition">
                <h4 className="font-medium text-gray-900 text-sm">{source.title}</h4>
                <p className="text-xs text-gray-600 mt-1 truncate">{source.url || t('copilot.noLink')}</p>
                {source.url ? (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 inline-flex h-8 w-full items-center justify-center rounded-lg border-2 border-gray-300 bg-white px-3 text-sm font-medium text-gray-800 transition-colors hover:border-gray-400 hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  >
                    {t('copilot.viewSource')}
                  </a>
                ) : null}
              </div>
            ))}
          
          {messages.length === 0 && (
            <div className="text-center py-8">
              <p className="text-sm text-gray-600">{t('copilot.sourcesEmpty')}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default RegulatoryCourtilot
