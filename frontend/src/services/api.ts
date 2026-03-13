import axios from 'axios'
import type { AxiosError } from 'axios'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  timeout: 15_000,
  headers: { 'Content-Type': 'application/json' },
})

// Normalize error responses into plain Error objects
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const rawDetail = (error.response?.data as { detail?: unknown } | undefined)?.detail
    const detail = typeof rawDetail === 'string' ? rawDetail : undefined
    const message = detail ?? error.message ?? 'An unexpected error occurred'
    return Promise.reject(new Error(message))
  },
)
