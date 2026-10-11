import React, { useEffect, useRef } from 'react'
import Icon from './Icons'

const QUICK_PROMPTS = [
  'Why is my code wrong?',
  'Explain the time complexity',
  'How can I optimize this?',
  'What edge cases am I missing?',
]

/** Chat with the AI coach about the code in the editor. State lives in the parent. */
export default function CoachChat({ messages, input, setInput, loading, onSend, onClear, className = '' }) {
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'nearest' })
  }, [messages, loading])

  return (
    <section className={`panel overflow-hidden ${className}`}>
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <h3 className="font-bold">Ask the coach</h3>
        {messages.length > 0 && (
          <button onClick={onClear} className="text-sm font-medium text-ink-3 hover:text-ink">
            Clear chat
          </button>
        )}
      </div>

      <div className="max-h-80 space-y-3 overflow-y-auto px-4 py-4">
        {messages.length === 0 ? (
          <div>
            <p className="text-sm text-ink-2">Ask anything about your code, for example “Why is my solution O(n²)?”</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {QUICK_PROMPTS.map((q) => (
                <button
                  key={q}
                  onClick={() => onSend(q)}
                  disabled={loading}
                  className="chip h-8 px-3 text-sm transition-colors hover:border-ink hover:text-ink disabled:opacity-50"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[88%] whitespace-pre-wrap rounded-lg px-3.5 py-2.5 text-sm leading-6 ${
                  m.role === 'user' ? 'bg-ink text-paper' : 'border border-line bg-sunken text-ink'
                }`}
              >
                {m.content}
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex items-center gap-2 text-sm text-ink-3" role="status">
            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-line-strong border-t-ink" />
            The coach is thinking
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="border-t border-line p-3">
        <div className="flex items-end gap-2">
          <label htmlFor="coach-input" className="sr-only">Message the coach</label>
          <textarea
            id="coach-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                onSend()
              }
            }}
            placeholder="Ask about your code"
            disabled={loading}
            rows={1}
            className="field min-h-[40px] flex-1 resize-none py-2 text-sm"
            style={{ maxHeight: 96 }}
          />
          <button
            onClick={() => onSend()}
            disabled={loading || !input.trim()}
            className="btn btn-primary btn-icon h-10 w-10"
            aria-label="Send message"
          >
            <Icon name="send" size={16} />
          </button>
        </div>
        <p className="mt-2 text-xs text-ink-3">Enter to send, Shift and Enter for a new line. Powered by NVIDIA NIM.</p>
      </div>
    </section>
  )
}
