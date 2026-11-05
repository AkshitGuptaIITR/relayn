import type { ApiError } from '../types/auth'

let csrfToken: string | null = null

export function setCsrfToken(token: string | null) {
  csrfToken = token
}

export function getCsrfToken(): string | null {
  return csrfToken
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers || {})

  if (!headers.has('Content-Type') && options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  // Inject CSRF token on state-changing requests
  const method = (options.method || 'GET').toUpperCase()
  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method) && csrfToken) {
    headers.set('x-csrf-token', csrfToken)
  }

  const response = await fetch(endpoint, {
    ...options,
    headers,
    credentials: 'include', // Include relayn_session cookie
  })

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}`
    try {
      const errorJson: ApiError = await response.json()
      errorDetail = errorJson.detail || errorJson.message || errorJson.error || errorDetail
    } catch {
      // Fallback to text if JSON parsing fails
      const text = await response.text()
      if (text) errorDetail = text
    }
    throw new Error(errorDetail)
  }

  // Handle empty 204 or responses with no body
  if (response.status === 204) {
    return {} as T
  }

  return response.json()
}
