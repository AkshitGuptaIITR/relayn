export interface SettingsData {
  timezone: string
  is_demo_mode: boolean
  is_setup_completed: boolean
  mailbox_email?: string | null
  sync_status: string
  has_google_credentials: boolean
  ai_provider: string
}

export interface LifecycleActionResponse {
  message: string
  status: string
}
