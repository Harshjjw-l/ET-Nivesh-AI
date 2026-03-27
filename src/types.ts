export type Timeframe = 'intraday' | 'short_term' | 'long_term'

export type Portfolio = {
  tickers: string[]
  amountInr: number | null
  timeframe: Timeframe
}

export type ChatRequest = {
  question: string
  portfolio: Portfolio
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
}

