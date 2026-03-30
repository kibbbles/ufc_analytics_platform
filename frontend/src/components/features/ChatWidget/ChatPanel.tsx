import { useState, useRef, useEffect } from 'react'
import { chatService } from '@services/chatService'
import type { ChatMessage } from '@services/chatService'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Message {
  role: 'user' | 'assistant'
  content: string
  sql?: string | null
  status?: string
}

interface Props {
  onClose: () => void
}

// ---------------------------------------------------------------------------
// ChatPanel
// ---------------------------------------------------------------------------

export default function ChatPanel({ onClose }: Props) {
  const [messages, setMessages]   = useState<Message[]>([])
  const [input, setInput]         = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [rateLimited, setRateLimited] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef  = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  // Focus input on open
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  async function send() {
    const question = input.trim()
    if (!question || isLoading || rateLimited) return

    const userMsg: Message = { role: 'user', content: question }
    const history: ChatMessage[] = messages
      .filter((m) => m.status !== 'error')
      .map((m) => ({ role: m.role, content: m.content }))

    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setIsLoading(true)

    try {
      const resp = await chatService.send({ question, history })
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: resp.answer,
          sql: resp.sql,
          status: resp.status,
        },
      ])
      if (resp.status === 'limit_reached') setRateLimited(true)
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Something went wrong. Please try again.', status: 'error' },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  const sendDisabled = isLoading || rateLimited || !input.trim()
  const sendTitle    = rateLimited
    ? 'Rate limit reached. Try again tomorrow.'
    : isLoading
    ? 'Waiting for response…'
    : undefined

  return (
    <div className="flex flex-col w-[calc(100vw-24px)] max-w-[360px] h-[520px] rounded-xl border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] shadow-2xl overflow-hidden">

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border-light)] dark:border-[var(--color-border)] shrink-0">
        <div>
          <p className="text-sm font-bold leading-tight">Ask the Maybe</p>
          <p className="text-[11px] text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
            Fights, fighters, records — powered by live data
          </p>
        </div>
        <button
          onClick={onClose}
          aria-label="Close chat"
          className="rounded-md p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary-light)] dark:hover:text-[var(--color-text-primary)] transition-colors"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center gap-3 py-6">
            <p className="text-sm text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
              Try asking:
            </p>
            {[
              "What is Khabib's UFC record?",
              'Who has the most KO wins at lightweight?',
              'How did the Adesanya vs Pyfer fight end?',
            ].map((q) => (
              <button
                key={q}
                onClick={() => { setInput(q); inputRef.current?.focus() }}
                className="text-xs px-3 py-1.5 rounded-full border border-[var(--color-border-light)] dark:border-[var(--color-border)] hover:border-[var(--color-primary)]/50 text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[85%] rounded-xl px-3 py-2 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-[var(--color-primary)] text-white rounded-br-sm'
                  : 'bg-[var(--color-surface-high-light)] dark:bg-[var(--color-surface-high)] text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)] rounded-bl-sm'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>

              {/* Collapsible SQL */}
              {msg.role === 'assistant' && msg.sql && (
                <details className="mt-2">
                  <summary className="text-[11px] cursor-pointer text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary-light)] dark:hover:text-[var(--color-text-secondary)] select-none">
                    View SQL
                  </summary>
                  <pre className="mt-1.5 text-[10px] overflow-x-auto rounded bg-[var(--color-border-light)] dark:bg-[var(--color-surface)] p-2 text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] whitespace-pre-wrap break-words">
                    {msg.sql}
                  </pre>
                </details>
              )}
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-[var(--color-surface-high-light)] dark:bg-[var(--color-surface-high)] rounded-xl rounded-bl-sm px-4 py-3">
              <span className="flex gap-1 items-center">
                {[0, 1, 2].map((d) => (
                  <span
                    key={d}
                    className="w-1.5 h-1.5 rounded-full bg-[var(--color-text-muted)] animate-bounce"
                    style={{ animationDelay: `${d * 0.15}s` }}
                  />
                ))}
              </span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="px-3 pb-3 pt-2 shrink-0 border-t border-[var(--color-border-light)] dark:border-[var(--color-border)]">
        {rateLimited && (
          <p className="text-[11px] text-amber-500 mb-1.5">
            Daily limit reached. Chat resets tomorrow.
          </p>
        )}
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about any fighter or fight…"
            rows={1}
            disabled={rateLimited}
            className="flex-1 resize-none rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-3 py-2 text-sm placeholder:text-[var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] disabled:opacity-50 max-h-24 overflow-y-auto"
            style={{ fieldSizing: 'content' } as React.CSSProperties}
          />
          <button
            onClick={send}
            disabled={sendDisabled}
            title={sendTitle}
            aria-label="Send message"
            className="shrink-0 rounded-lg bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] disabled:opacity-40 disabled:cursor-not-allowed text-white p-2.5 transition-colors"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </button>
        </div>
        <p className="mt-1.5 text-[10px] text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)] text-center">
          Powered by Groq · Data through last Sunday
        </p>
      </div>
    </div>
  )
}
