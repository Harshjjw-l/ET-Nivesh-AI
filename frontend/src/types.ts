export type Timeframe = 'intraday' | 'short_term' | 'long_term'

export type Portfolio = {
  tickers: string[]
  amountInr: number | null
  timeframe: Timeframe
}

export type ChatRequest = {
  question: string
  portfolio: string[]
  investment_amount: number
  timeframe: string
}

export type SourceItem = {
  timestamp: string
  dataUsed: string
}

export type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: SourceItem[]
  indicators?: {
    rsi?: number | string | null
    macdSignal?: string | null
  }

  entry_price?: string | number | null
  target_price?: string | number | null
  stop_loss?: string | number | null
  rsi_explanation?: string
  budget_note?: string | null
  concentration_warning?: string | null
  bulk_deals?: unknown
}

export type BulkDeal = {
  symbol?: string
  securityName?: string
  secName?: string
  clientName?: string
  quantityTraded?: number | string
  tradedQty?: number | string
  buySell?: string
  action?: string
  price?: number | string
  dealDate?: string
  [key: string]: unknown
}