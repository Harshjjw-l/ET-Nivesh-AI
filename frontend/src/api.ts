import type { ChatRequest } from './types'
import type { BulkDeal } from './types'

const API_BASE =
  import.meta.env.VITE_API_URL || 'https://et-nivesh-ai-backend1.onrender.com'

export type ChatResponse = {
  answer?: string
  entry_price?: string | number | null
  target_price?: string | number | null
  stop_loss?: string | number | null
  rsi_value?: number | string | null
  rsi_explanation?: string
  sources_used?: string[]
  timestamp?: string
  concentration_warning?: string | null
  bulk_deals?: unknown
  budget_note?: string | null

  status?: 'ok' | 'need_selection'
  options?: {
    symbol: string
    company_name: string
    ticker: string
  }[]
}

export async function postChat(payload: ChatRequest, signal?: AbortSignal) {
  const res = await fetch(`${API_BASE}/chat`, {
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
  return data
}

type TodaySignalsResponse = {
  timestamp: string
  deals: BulkDeal[]
}

export async function getTodaySignals(signal?: AbortSignal) {
  const res = await fetch(`${API_BASE}/signals/today`, {
    method: 'GET',
    signal,
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Signals request failed (${res.status}): ${text || res.statusText}`)
  }

  const data = (await res.json()) as TodaySignalsResponse
  return {
    timestamp: data.timestamp,
    deals: Array.isArray(data.deals) ? data.deals : [],
  }
}
export async function searchStock(query: string, signal?: AbortSignal) {
  const res = await fetch(`${API_BASE}/search-stock?q=${encodeURIComponent(query)}`, {
    method: 'GET',
    signal,
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Search stock failed (${res.status}): ${text || res.statusText}`)
  }

  const data = await res.json()
  return Array.isArray(data.results) ? data.results : []
}
