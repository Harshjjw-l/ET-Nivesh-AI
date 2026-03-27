import { useMemo, useRef, useState } from 'react'
import type { ChatMessage, Portfolio, Timeframe } from './types'
import { postChat } from './api'

const BRAND_ORANGE = '#FF6B35'
const BRAND_NAVY = '#1B2B4B'

function nowIso() {
  return new Date().toISOString()
}

function formatTime(iso: string) {
  const d = new Date(iso)
  return d.toLocaleString()
}

function normalizeTicker(s: string) {
  return s.trim().toUpperCase().replace(/\s+/g, '')
}

function uniqueNonEmptyTickers(values: string[]) {
  const out: string[] = []
  const seen = new Set<string>()
  for (const v of values) {
    const t = normalizeTicker(v)
    if (!t) continue
    if (seen.has(t)) continue
    seen.add(t)
    out.push(t)
  }
  return out.slice(0, 5)
}

export function App() {
  const [tickerInputs, setTickerInputs] = useState<string[]>(['', '', '', '', ''])
  const [amountInr, setAmountInr] = useState<string>('')
  const [timeframe, setTimeframe] = useState<Timeframe>('short_term')

  const portfolio: Portfolio = useMemo(() => {
    const tickers = uniqueNonEmptyTickers(tickerInputs)
    const n = amountInr.trim() === '' ? null : Number(amountInr)
    return {
      tickers,
      amountInr: Number.isFinite(n as number) ? (n as number) : null,
      timeframe,
    }
  }, [tickerInputs, amountInr, timeframe])

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: crypto.randomUUID(),
      role: 'assistant',
      content:
        'Hi — I’m ET Nivesh AI. Add your portfolio in the left panel, then ask a question like “How should I allocate across these for a 3-month view?”',
      sources: [{ timestamp: nowIso(), dataUsed: 'No external data (welcome message)' }],
    },
  ])
  const [question, setQuestion] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  async function onSend() {
    const q = question.trim()
    if (!q || isSending) return

    setError(null)
    setQuestion('')

    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: 'user', content: q }
    setMessages((m) => [...m, userMsg])

    setIsSending(true)
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    try {
      const payload = { question: q, portfolio }
      const { answer, sources } = await postChat(payload, controller.signal)

      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: answer || '(No response returned.)',
        sources:
          sources && sources.length
            ? sources
            : [
                {
                  timestamp: nowIso(),
                  dataUsed: `Payload: { tickers: [${portfolio.tickers.join(', ')}], amountInr: ${
                    portfolio.amountInr ?? 'null'
                  }, timeframe: ${portfolio.timeframe} }`,
                },
              ],
      }
      setMessages((m) => [...m, assistantMsg])
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Unknown error'
      setError(msg)
      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content:
            "I couldn't reach the chat server. Please make sure your backend is running on `http://localhost:8000/chat` and supports CORS.",
          sources: [{ timestamp: nowIso(), dataUsed: `Error: ${msg}` }],
        },
      ])
    } finally {
      setIsSending(false)
    }
  }

  return (
    <div className="app" style={{ ['--brand-orange' as never]: BRAND_ORANGE, ['--brand-navy' as never]: BRAND_NAVY }}>
      <aside className="sidebar">
        <div className="brand">
          <div className="brandMark" aria-hidden="true" />
          <div>
            <div className="brandName">ET Nivesh AI</div>
            <div className="brandTag">Portfolio + Market Chat</div>
          </div>
        </div>

        <div className="panel">
          <div className="panelTitle">Portfolio</div>

          <div className="fieldGroup">
            <label className="label">Stock tickers (up to 5)</label>
            <div className="tickers">
              {tickerInputs.map((v, i) => (
                <input
                  key={i}
                  className="input"
                  value={v}
                  placeholder={i === 0 ? 'e.g. RELIANCE' : 'optional'}
                  onChange={(e) => {
                    const next = tickerInputs.slice()
                    next[i] = e.target.value
                    setTickerInputs(next)
                  }}
                />
              ))}
            </div>
            <div className="hint">
              Active: <span className="chip">{portfolio.tickers.length ? portfolio.tickers.join(', ') : '—'}</span>
            </div>
          </div>

          <div className="fieldGroup">
            <label className="label" htmlFor="amount">
              Investment amount (₹)
            </label>
            <input
              id="amount"
              className="input"
              inputMode="numeric"
              placeholder="e.g. 250000"
              value={amountInr}
              onChange={(e) => setAmountInr(e.target.value.replace(/[^\d.]/g, ''))}
            />
          </div>

          <div className="fieldGroup">
            <label className="label" htmlFor="timeframe">
              Timeframe
            </label>
            <select
              id="timeframe"
              className="input select"
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value as Timeframe)}
            >
              <option value="intraday">Intraday</option>
              <option value="short_term">Short term</option>
              <option value="long_term">Long term</option>
            </select>
          </div>

          <div className="summary">
            <div className="summaryRow">
              <div className="summaryLabel">Tickers</div>
              <div className="summaryValue">{portfolio.tickers.length ? portfolio.tickers.length : '—'}</div>
            </div>
            <div className="summaryRow">
              <div className="summaryLabel">Amount</div>
              <div className="summaryValue">{portfolio.amountInr == null ? '—' : `₹${portfolio.amountInr}`}</div>
            </div>
            <div className="summaryRow">
              <div className="summaryLabel">Horizon</div>
              <div className="summaryValue">
                {timeframe === 'intraday' ? 'Intraday' : timeframe === 'short_term' ? 'Short term' : 'Long term'}
              </div>
            </div>
          </div>

          <div className="note">
            Tip: ask for allocation, risk, entry levels, or “what changed today?” based on your timeframe.
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="topTitle">Chat</div>
          <div className="topMeta">
            API: <span className="mono">POST localhost:8000/chat</span>
          </div>
        </header>

        <section className="chat">
          <div className="messages" role="log" aria-label="Chat messages">
            {messages.map((m) => (
              <div key={m.id} className={`msgRow ${m.role}`}>
                <div className={`bubble ${m.role}`}>
                  <div className="bubbleText">{m.content}</div>
                </div>

                {m.role === 'assistant' && m.sources && m.sources.length ? (
                  <div className="sourcesCard">
                    <div className="sourcesTitle">Sources</div>
                    <div className="sourcesList">
                      {m.sources.map((s, idx) => (
                        <div className="sourceItem" key={idx}>
                          <div className="sourceTime">{formatTime(s.timestamp)}</div>
                          <div className="sourceData">{s.dataUsed}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            ))}
          </div>

          <div className="composer">
            {error ? <div className="error">{error}</div> : null}
            <div className="composerRow">
              <input
                className="input composerInput"
                placeholder="Ask a question…"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) onSend()
                }}
              />
              <button className="sendBtn" onClick={onSend} disabled={isSending || !question.trim()}>
                {isSending ? 'Sending…' : 'Send'}
              </button>
            </div>
            <div className="composerHint">
              Portfolio is sent with every question: <span className="mono">{JSON.stringify(portfolio)}</span>
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}

