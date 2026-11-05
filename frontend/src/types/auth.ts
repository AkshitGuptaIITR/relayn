export interface AuthStatus {
  authenticated: boolean
  csrf_token?: string | null
  timezone: string
  is_setup_completed: boolean
  is_demo_mode: boolean
}

export interface ApiError {
  error?: string
  message?: string
  detail?: string
}
