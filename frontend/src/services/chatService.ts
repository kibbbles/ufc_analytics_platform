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
  status: 'ok' | 'limit_reached' | 'no_results' | 'error'
}

export const chatService = {
  send(request: ChatRequest): Promise<ChatResponse> {
    return apiClient
      .post<ChatResponse>('/chat', request)
      .then((r) => r.data)
  },
}
