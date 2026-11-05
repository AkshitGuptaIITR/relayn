export interface JobStatus {
  sync_status: 'idle' | 'syncing' | 'error' | 'disconnected'
  last_synced_at?: string | null
  last_history_id?: string | null
  sync_error?: string | null
  queued_jobs: number
  running_jobs: number
  completed_jobs: number
  failed_jobs: number
  total_messages: number
}

export interface SyncTriggerResponse {
  message: string
  job_id?: string | null
  new_messages: number
}
