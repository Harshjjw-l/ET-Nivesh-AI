import { useEffect, useMemo, useRef, useState } from 'react'
import type { BulkDeal, ChatMessage, Portfolio, Timeframe, StockSuggestion } from './types'
import { getTodaySignals, postChat, searchStock } from './api'

function nowIso() {
  return new Date().toISOString()
}



function normalizeTicker(s: string) {
  return s.trim().toUpperCase().replace(/\s+/g, '')
}

function indicatorTone(macdSignal?: string | null) {
  const signal = (macdSignal || '').toLowerCase()
  if (signal.includes('bullish')) return 'bullish'
  if (signal.includes('bearish')) return 'bearish'
  return 'neutral'
}

function indicatorToneClasses(macdSignal?: string | null) {
  const tone = indicatorTone(macdSignal)
  if (tone === 'bullish') return 'border-emerald-400/50 bg-emerald-500/10'
  if (tone === 'bearish') return 'border-red-400/50 bg-red-500/10'
  return 'border-white/15 bg-white/5'
}
function formatTime(iso?: string) {
  if (!iso) return 'No timestamp'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  return d.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  })
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

function stockNameFromDeal(deal: BulkDeal) {
  return String(deal.securityName || deal.secName || deal.symbol || 'Unknown stock')
}

function dealSummaryFromDeal(deal: BulkDeal) {
  const side = String(deal.buySell || deal.action || 'Deal')
  const qty = deal.quantityTraded ?? deal.tradedQty
  const qtyText = qty == null ? '' : ` | Qty: ${qty}`
  const priceText = deal.price == null ? '' : ` | Price: ${deal.price}`
  return `${side}${qtyText}${priceText}`.trim()
}

export default function App() {
  const [tickerInputs, setTickerInputs] = useState<string[]>(['', '', '', '', ''])
  const [amountInr, setAmountInr] = useState<string>('')
  const [totalInvested, setTotalInvested] = useState<string>('')
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
  const [todaySignals, setTodaySignals] = useState<BulkDeal[]>([])
  const [signalsError, setSignalsError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const [suggestions, setSuggestions] = useState<Record<number, StockSuggestion[]>>({})
  const searchAbortRef = useRef<AbortController | null>(null)
  useEffect(() => {
    const controller = new AbortController()
    getTodaySignals(controller.signal)
      .then(({ deals }) => {
        setTodaySignals(deals.slice(0, 3))
        setSignalsError(null)
      })
      .catch((e) => {
        const msg = e instanceof Error ? e.message : 'Failed to load today signals'
        setSignalsError(msg)
      })
      
    return () => controller.abort()
  }, [])
  async function handleTickerSearch(value: string, index: number) {
    const cleaned = value.trim()
  
    if (!cleaned) {
      setSuggestions((prev) => ({ ...prev, [index]: [] }))
      return
    }
  
    searchAbortRef.current?.abort()
    const controller = new AbortController()
    searchAbortRef.current = controller
  
    try {
      const results = await searchStock(cleaned, controller.signal)
      setSuggestions((prev) => ({ ...prev, [index]: results }))
    } catch {
      setSuggestions((prev) => ({ ...prev, [index]: [] }))
    }
  }
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
        const payload = {
        question: q,
        portfolio: portfolio.tickers,
        investment_amount: portfolio.amountInr ?? 0,
        total_invested: Number(totalInvested) || 0,
        timeframe:
          portfolio.timeframe === 'intraday'
            ? 'intraday'
            : portfolio.timeframe === 'short_term'
            ? '1 month'
            : '12 month',
      }
      const result : any = await postChat(payload, controller.signal)
      if (result.status === 'need_selection' && result.options?.length) {
        const assistantMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: 'I found multiple matching stocks. Please choose one:',
          options: result.options,
          sources: [
            {
              timestamp: nowIso(),
              dataUsed: 'Ambiguous stock detected — user selection required',
            },
          ],
        }
      
        setMessages((m) => [...m, assistantMsg])
        return
      }



      if (result.status === 'need_selection'  && result.options?.length) {
        const assistantMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: 'Multiple stocks found. Please select one:',
          options: result.options,
          sources: [
            {
              timestamp: result.timestamp || nowIso(),
              dataUsed: 'Multiple matching stock symbols found',
            },
          ],
        } // NEW FIELD
        
      
        setMessages((m) => [...m, assistantMsg])
        setIsSending(false)
        return
      }
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: result.answer || '(No response returned.)',
        indicators:
          result.rsi_value != null
            ? {
                rsi: result.rsi_value,
                macdSignal: undefined,
              }
            : undefined,
            sources:
            result.sources_used && result.sources_used.length
              ? result.sources_used.map((s: string) => ({
                  timestamp: nowIso(),
                  dataUsed: s,
                }))
            : [
                {
                  timestamp: nowIso(),
                  dataUsed: `Payload: { tickers: [${portfolio.tickers.join(', ')}], amountInr: ${
                    portfolio.amountInr ?? 'null'
                  }, timeframe: ${portfolio.timeframe} }`,
                },
              ],
      
        // NEW backend fields
        entry_price: result.entry_price,
        target_price: result.target_price,
        stop_loss: result.stop_loss,
        rsi_explanation: result.rsi_explanation,
        budget_note: result.budget_note,
        concentration_warning: result.concentration_warning,
        bulk_deals: result.bulk_deals,
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
  const quickQuestions = [
    "Should I buy these stocks?",
    "How is my portfolio doing overall?",
    "Any risk in my portfolio?",
    "What are best entry levels?",
  ]
  return (
    <div className="min-h-screen bg-slate-950 text-white">
    <div className="mx-auto grid min-h-screen max-w-[1600px] grid-cols-1 md:grid-cols-[340px_1fr]">
        <aside className="border-b border-white/10 bg-slate-900/70 p-4 md:border-r md:border-b-0 md:p-5">
          <div className="rounded-2xl border border-white/15 bg-black/20 p-3">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-orange-500 to-orange-300/30" aria-hidden="true" />
              <div>
                <div className="font-semibold tracking-wide">ET Nivesh AI</div>
                <div className="text-xs text-white/70">Portfolio + Market Chat</div>
              </div>
            </div>
          </div>

          <div className="mt-4 rounded-2xl border border-white/15 bg-white/5 p-4">
            <div className="mb-3 text-sm font-semibold">Portfolio</div>

            <div className="mb-4">
              <label className="mb-2 block text-xs text-white/70">Stock tickers (up to 5)</label>
              <div className="grid grid-cols-1 gap-2">
              {tickerInputs.map((v, i) => (
  <div key={i} className="space-y-2">
    <input
      className="w-full rounded-xl border border-white/15 bg-black/20 px-3 py-2.5 text-sm text-white outline-none transition focus:border-orange-400/70 focus:ring-2 focus:ring-orange-400/30"
      value={v}
      placeholder={i === 0 ? 'e.g. RELIANCE' : 'optional'}
      onChange={(e) => {
        const next = tickerInputs.slice()
        next[i] = e.target.value
        setTickerInputs(next)
        handleTickerSearch(e.target.value, i)
      }}
    />

    {suggestions[i] && suggestions[i].length > 0 && v.trim() ? (
      <div className="flex flex-wrap gap-2">
        {suggestions[i].map((s, idx) => (
          <button
            key={`${s.symbol}-${idx}`}
            type="button"
            className="rounded-full border border-orange-400/30 bg-orange-500/10 px-3 py-1 text-xs text-orange-100 hover:bg-orange-500/20"
            onClick={() => {
              const next = tickerInputs.slice()
              next[i] = s.symbol
              setTickerInputs(next)
              setSuggestions((prev) => ({ ...prev, [i]: [] }))
            }}
          >
            {s.symbol} - {s.company_name}
          </button>
        ))}
      </div>
    ) : null}
  </div>
))}
              </div>
              <div className="mt-2 text-xs text-white/65">
                Active:{' '}
                <span className="rounded-full border border-white/15 bg-black/20 px-2 py-0.5 text-white/85">
                  {portfolio.tickers.length ? portfolio.tickers.join(', ') : '—'}
                </span>
              </div>
            </div>
            <div className="mb-4">
  <label className="mb-2 block text-xs text-white/70" htmlFor="totalInvested">
    Total already invested (₹)
  </label>
  <input
    id="totalInvested"
    className="w-full rounded-xl border border-white/15 bg-black/20 px-3 py-2.5 text-sm text-white outline-none transition focus:border-orange-400/70 focus:ring-2 focus:ring-orange-400/30"
    inputMode="numeric"
    placeholder="e.g. 500000"
    value={totalInvested}
    onChange={(e) => setTotalInvested(e.target.value.replace(/[^\d.]/g, ''))}
  />
</div>
            <div className="mb-4">
              <label className="mb-2 block text-xs text-white/70" htmlFor="amount">
                Available amount to invest now (₹)
              </label>
              <input
                id="amount"
                className="w-full rounded-xl border border-white/15 bg-black/20 px-3 py-2.5 text-sm text-white outline-none transition focus:border-orange-400/70 focus:ring-2 focus:ring-orange-400/30"
                inputMode="numeric"
                placeholder="e.g. 250000"
                value={amountInr}
                onChange={(e) => setAmountInr(e.target.value.replace(/[^\d.]/g, ''))}
              />
            </div>

            <div className="mb-4">
              <label className="mb-2 block text-xs text-white/70" htmlFor="timeframe">
                Timeframe
              </label>
              <select
                id="timeframe"
                className="w-full rounded-xl border border-white/15 bg-black/20 px-3 py-2.5 text-sm text-white outline-none transition focus:border-orange-400/70 focus:ring-2 focus:ring-orange-400/30"
                value={timeframe}
                onChange={(e) => setTimeframe(e.target.value as Timeframe)}
              >
                <option value="intraday">Intraday</option>
                <option value="short_term">Short term</option>
                <option value="long_term">Long term</option>
              </select>
            </div>

            <div className="rounded-xl border border-dashed border-white/20 bg-black/20 p-3 text-xs">
              <div className="flex items-center justify-between py-1">
                <span className="text-white/65">Tickers</span>
                <span className="text-white/90">{portfolio.tickers.length ? portfolio.tickers.length : '—'}</span>
              </div>
              <div className="flex items-center justify-between py-1">
  <span className="text-white/65">Already Invested</span>
  <span className="text-white/90">{totalInvested ? `₹${totalInvested}` : '—'}</span>
</div>

<div className="flex items-center justify-between py-1">
  <span className="text-white/65">Available Cash</span>
  <span className="text-white/90">{portfolio.amountInr == null ? '—' : `₹${portfolio.amountInr}`}</span>
</div>
              <div className="flex items-center justify-between py-1">
                <span className="text-white/65">Horizon</span>
                <span className="text-white/90">
                  {timeframe === 'intraday' ? 'Intraday' : timeframe === 'short_term' ? 'Short term' : 'Long term'}
                </span>
              </div>
            </div>

            <div className="mt-3 text-xs leading-5 text-white/65">
              Tip: ask for allocation, risk, entry levels, or "what changed today?" based on your timeframe.
            </div>
            <button
  className="mt-4 w-full rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm text-white/80 hover:bg-white/10"
  onClick={() => {
    setTickerInputs(['', '', '', '', ''])
    setAmountInr('')
    setTotalInvested('')
    setTimeframe('short_term')
  }}
>
  Reset Portfolio
</button>
          </div>
        </aside>

        <main className="flex min-h-0 flex-col">
        <header className="flex flex-col gap-2 border-b border-white/10 bg-black/20 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-5">
  <div className="font-semibold">Chat</div>

  <div className="flex items-center gap-2">
    <button
      className="rounded-lg border border-white/15 px-3 py-1 text-xs text-white/80 hover:bg-white/10"
      onClick={() =>
        setMessages([
          {
            id: crypto.randomUUID(),
            role: 'assistant',
            content:
              'Hi — I’m ET Nivesh AI. Add your portfolio in the left panel, then ask a question like “How should I allocate across these for a 3-month view?”',
            sources: [{ timestamp: nowIso(), dataUsed: 'No external data (welcome message)' }],
          },
        ])
      }
    >
      Clear Chat
    </button>

    <div className="text-xs text-white/70">
      API: <span className="font-mono">POST localhost:8000/chat</span>
    </div>
  </div>
</header>

          <section className="grid min-h-0 flex-1 grid-rows-[auto_1fr_auto]">
            <div className="px-4 pt-3 sm:px-5">
              <div className="mb-2 text-sm font-semibold text-white/90">Today's Signals</div>
              {signalsError ? (
                <div className="text-xs text-white/65">Unable to load signals right now.</div>
              ) : todaySignals.length ? (
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {todaySignals.map((deal, idx) => (
                    <div key={`${stockNameFromDeal(deal)}-${idx}`} className="rounded-xl border border-white/15 bg-white/5 p-3">
                      <div className="mb-1 text-sm font-semibold text-white/90">{stockNameFromDeal(deal)}</div>
                      <div className="text-xs leading-5 text-white/70">{dealSummaryFromDeal(deal)}</div>
                    </div>
                  ))}
                </div>
              
) : (
  <div className="rounded-xl border border-white/15 bg-white/5 p-3 text-xs text-white/75">
    No strong bulk deal signals found today. Check again during market hours.
  </div>
)}
            </div>

            <div className="overflow-y-auto px-4 py-4 sm:px-5" role="log" aria-label="Chat messages">
              {messages.map((m) => {
                const isUser = m.role === 'user'
                return (
                  <div key={m.id} className={`mb-4 flex flex-col gap-2 ${isUser ? 'items-end' : 'items-start'}`}>
                    <div
                      className={`w-full max-w-3xl rounded-2xl border px-4 py-3 text-sm leading-6 shadow-lg ${
                        isUser
                          ? 'border-orange-400/40 bg-orange-500/20'
                          : 'border-white/15 bg-white/10'
                      }`}
                    >
                      


                    
                    <div className="whitespace-pre-wrap break-words text-sm leading-7 text-white/95">
                    {m.content}
                    </div>

{m.role === 'assistant' && m.options && m.options.length > 0 && (
  <div className="mt-3 flex flex-wrap gap-2">
    {m.options.map((opt, idx) => (
      <button
        key={`${opt.symbol}-${idx}`}
        type="button"
        className="rounded-full border border-orange-400/30 bg-orange-500/10 px-3 py-1 text-xs text-orange-100 hover:bg-orange-500/20"
        onClick={() => {
          setQuestion(`Analyze ${opt.symbol}`)
        }}
      >
        {opt.symbol} - {opt.company_name}
      </button>
    ))}
  </div>
)}
                      {m.role === 'assistant' && (
  <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
    {m.entry_price && (
      <div className="rounded-2xl border border-emerald-400/30 bg-emerald-500/10 p-4 shadow-sm">
        <div className="text-xs uppercase tracking-wide text-emerald-200/80">Entry Price</div>
        <div className="mt-2 text-lg font-bold text-white">{m.entry_price}</div>
      </div>
    )}

    {m.target_price && (
      <div className="rounded-2xl border border-blue-400/30 bg-blue-500/10 p-4 shadow-sm">
        <div className="text-xs uppercase tracking-wide text-blue-200/80">Target Price</div>
        <div className="mt-2 text-lg font-bold text-white">₹{m.target_price}</div>
      </div>
    )}

    {m.stop_loss && (
      <div className="rounded-2xl border border-red-400/30 bg-red-500/10 p-4 shadow-sm">
        <div className="text-xs uppercase tracking-wide text-red-200/80">Stop Loss</div>
        <div className="mt-2 text-lg font-bold text-white">₹{m.stop_loss}</div>
      </div>
    )}
  </div>
)}
                    {m.role === 'assistant' && m.rsi_explanation ? (
                     <div className="mt-3 rounded-xl border border-yellow-400/30 bg-yellow-500/10 p-3 text-xs text-white/85">
                        <div className="mb-1 font-semibold text-white/90">RSI Explanation</div>
                        <div>{m.rsi_explanation}</div>
                      </div>
                    ) : null}
                    {m.role === 'assistant' && m.budget_note ? (
                     <div className="mt-3 rounded-xl border border-cyan-400/30 bg-cyan-500/10 p-3 text-xs text-white/85">
                      <div className="mb-1 font-semibold text-white/90">Budget Analysis</div>
                      <div>{m.budget_note}</div>
                     </div>
                    ) : null}
                    {m.role === 'assistant' && m.concentration_warning ? (
                     <div className="mt-3 rounded-xl border border-orange-400/30 bg-orange-500/10 p-3 text-xs text-white/85">
                       <div className="mb-1 font-semibold text-white/90">Risk Warning</div>
                       <div>{m.concentration_warning}</div>
                      </div>
                    ) : null}
                    </div>

                    {m.role === 'assistant' && m.sources && m.sources.length ? (
                      <div className="w-full max-w-3xl rounded-2xl border border-white/15 bg-black/20 p-3">
                        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-white/80">Sources</div>
                        <div className="grid gap-2">
                          {m.sources.map((s, idx) => (
                            <div className="rounded-xl border border-white/15 bg-white/5 p-3" key={idx}>
                              <div className="mb-1 text-xs text-white/60">{formatTime(s.timestamp)}</div>
                              <div className="break-words text-xs leading-5 text-white/85">{s.dataUsed}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {m.role === 'assistant' && m.indicators && (m.indicators.rsi != null || m.indicators.macdSignal) ? (
                      <div className={`w-full max-w-3xl rounded-xl border p-3 text-xs ${indicatorToneClasses(m.indicators.macdSignal)}`}>
                        <div className="mb-2 font-semibold text-white/90">Market signal</div>
                        <div className="flex items-center justify-between py-0.5">
                          <span className="text-white/70">RSI</span>
                          <span className="text-white/90">{m.indicators.rsi ?? '—'}</span>
                        </div>
                        <div className="flex items-center justify-between py-0.5">
                          <span className="text-white/70">MACD</span>
                          <span className="text-white/90">{m.indicators.macdSignal || '—'}</span>
                        </div>
                      </div>
                    ) : null}
                  </div>
                )
              })}
              {isSending && (
  <div className="mb-4 flex flex-col gap-2 items-start">
    <div className="w-full max-w-3xl rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-sm leading-6 shadow-lg">
      Thinking...
    </div>
  </div>
)}  
            </div>
            <div className="mb-2 flex flex-wrap gap-2">
  {quickQuestions.map((q, i) => (
    <button
      key={i}
      className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs text-white/80 hover:bg-white/10"
      onClick={() => {
        setQuestion(q)
      }}
    >
      {q}
    </button>
  ))}
</div>
            <div className="border-t border-white/10 bg-black/20 px-4 py-3 sm:px-5">
              {error ? (
                <div className="mb-2 rounded-xl border border-orange-400/40 bg-orange-500/15 px-3 py-2 text-xs text-orange-50">
                  {error}
                </div>
              ) : null}
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_auto] sm:items-center">
                <input
                  className="h-11 w-full rounded-xl border border-white/15 bg-black/20 px-3 text-sm text-white outline-none transition focus:border-orange-400/70 focus:ring-2 focus:ring-orange-400/30"
                  placeholder="Ask a question..."
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) onSend()
                  }}
                />
                <button
                  className="h-11 rounded-xl border border-orange-400/50 bg-gradient-to-br from-orange-500 to-orange-400 px-4 font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60"
                  onClick={onSend}

                  disabled={isSending || !question.trim()}
                >
                  {isSending ? 'Sending...' : 'Send'}
                </button>
              </div>
              <div className="mt-2 break-all text-[11px] text-white/55 sm:text-xs">
                Portfolio is sent with every question: <span className="font-mono">{JSON.stringify(portfolio)}</span>
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  )
}