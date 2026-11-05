import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Database } from 'lucide-react'
import { apiClient } from '../../lib/api'
import type { JobStatus, SyncTriggerResponse } from '../../types/sync'

export function SyncControlPanel() {
  const queryClient = useQueryClient()
  const [feedback, setFeedback] = useState<string | null>(null)

  // Poll sync status every 5 seconds
  const { data: status } = useQuery<JobStatus>({
    queryKey: ['sync-status'],
    queryFn: () => apiClient<JobStatus>('/api/sync/status'),
    refetchInterval: 5000,
  })

  // Trigger sync mutation
  const syncMutation = useMutation<SyncTriggerResponse, Error>({
    mutationFn: () => apiClient<SyncTriggerResponse>('/api/sync/trigger', { method: 'POST' }),
    onSuccess: (data: SyncTriggerResponse) => {
      setFeedback(data.message)
      queryClient.invalidateQueries({ queryKey: ['sync-status'] })
      setTimeout(() => setFeedback(null), 6000)
    },
    onError: (err: Error) => {
      setFeedback(`Error: ${err.message}`)
    },
  })

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Database className="w-4 h-4 text-indigo-400" />
            Mailbox Synchronization
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Mode: <span className="text-slate-200 font-medium">Synthetic Ingestion (Offline Fixtures)</span>
          </p>
        </div>

        <button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending || status?.sync_status === 'syncing'}
          className="inline-flex items-center justify-center px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-xs font-semibold text-white rounded-lg transition shadow cursor-pointer shrink-0"
        >
          <RefreshCw
            className={`w-3.5 h-3.5 mr-2 ${
              syncMutation.isPending || status?.sync_status === 'syncing' ? 'animate-spin' : ''
            }`}
          />
          {syncMutation.isPending || status?.sync_status === 'syncing' ? 'Syncing...' : 'Sync Mailbox Now'}
        </button>
      </div>

      {feedback && (
        <div className="rounded-lg bg-indigo-500/10 border border-indigo-500/20 px-3 py-2 text-xs text-indigo-300">
          {feedback}
        </div>
      )}

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 border-t border-slate-800/80">
        <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/60">
          <div className="text-[11px] text-slate-400 font-medium">Imported Messages</div>
          <div className="text-lg font-bold text-white mt-0.5">{status?.total_messages ?? 0}</div>
        </div>

        <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/60">
          <div className="text-[11px] text-slate-400 font-medium">Queued Jobs</div>
          <div className="text-lg font-bold text-amber-400 mt-0.5">{status?.queued_jobs ?? 0}</div>
        </div>

        <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/60">
          <div className="text-[11px] text-slate-400 font-medium">Completed Jobs</div>
          <div className="text-lg font-bold text-emerald-400 mt-0.5">{status?.completed_jobs ?? 0}</div>
        </div>

        <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/60">
          <div className="text-[11px] text-slate-400 font-medium">Sync Status</div>
          <div className="text-xs font-semibold capitalize mt-1.5 flex items-center gap-1.5">
            <span
              className={`w-2 h-2 rounded-full ${
                status?.sync_status === 'syncing'
                  ? 'bg-amber-400 animate-pulse'
                  : status?.sync_status === 'error'
                  ? 'bg-rose-500'
                  : 'bg-emerald-400'
              }`}
            />
            <span className="text-slate-200">{status?.sync_status ?? 'idle'}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
