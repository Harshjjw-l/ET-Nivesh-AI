import type { ChatRequest, SourceItem } from './types'

type ChatResponse =
  | {
      answer: string
      sources?: SourceItem[]
    }
  | {
      response: string
      sources?: SourceItem[]
    }
  | {
      message: string
      sources?: SourceItem[]
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

  return { answer, sources }
}

