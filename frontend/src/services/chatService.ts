import { apiClient } from './api'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatRequest {
  question: string
  history: ChatMessage[]
}

export interface ChatResponse {
  answer: string
  sql: string | null
  status: 'ok' | 'rate_limited' | 'no_results' | 'error'
  retry_after?: number
}

export const chatService = {
  send(request: ChatRequest): Promise<ChatResponse> {
    return apiClient
      .post<ChatResponse>('/chat', request)
      .then((r) => r.data)
  },
}
