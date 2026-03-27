import type { ChatRequest, SourceItem } from './types'
import type { BulkDeal } from './types'

type ChatResponse =
  | {
      answer: string
      sources?: SourceItem[]
      rsi?: number | string | null
      macdSignal?: string | null
      macd_signal?: string | null
    }
  | {
      response: string
      sources?: SourceItem[]
      rsi?: number | string | null
      macdSignal?: string | null
      macd_signal?: string | null
    }
  | {
      message: string
      sources?: SourceItem[]
      rsi?: number | string | null
      macdSignal?: string | null
      macd_signal?: string | null
    }

export async function postChat(payload: ChatRequest, signal?: AbortSignal) {
  const res = await fetch('http://localhost:8000/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Chat request failed (${res.status}): ${text || res.statusText}`)
  }

  const data = (await res.json()) as ChatResponse
  const answer =
    'answer' in data ? data.answer : 'response' in data ? data.response : 'message' in data ? data.message : ''
  const sources = 'sources' in data ? data.sources : undefined
  const rsi = 'rsi' in data ? data.rsi : undefined
  const macdSignal = 'macdSignal' in data ? data.macdSignal : 'macd_signal' in data ? data.macd_signal : undefined

  return { answer, sources, rsi, macdSignal }
}

type TodaySignalsResponse = {
  timestamp: string
  deals: BulkDeal[]
}

export async function getTodaySignals(signal?: AbortSignal) {
  const res = await fetch('http://localhost:8000/signals/today', {
    method: 'GET',
    signal,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Signals request failed (${res.status}): ${text || res.statusText}`)
  }
  const data = (await res.json()) as TodaySignalsResponse
  return { timestamp: data.timestamp, deals: Array.isArray(data.deals) ? data.deals : [] }
}

