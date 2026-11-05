import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Settings as SettingsIcon,
  Mail,
  Trash2,
  Unlink,
  Bot,
} from 'lucide-react'
import { apiClient } from '../../lib/api'
import type { SettingsData, LifecycleActionResponse } from '../../types/settings'

export function SettingsPage() {
  const queryClient = useQueryClient()
  const [feedback, setFeedback] = useState<string | null>(null)
  const [isConfirmingPurge, setIsConfirmingPurge] = useState(false)

  const { data: settings, isLoading } = useQuery<SettingsData>({
    queryKey: ['settings'],
    queryFn: () => apiClient<SettingsData>('/api/settings'),
  })

  // Connect Google mutation
  const connectGoogleMutation = useMutation({
    mutationFn: () => apiClient<{ authorization_url: string }>('/api/auth/google/connect'),
    onSuccess: (data) => {
      // Redirect to Google consent screen
      window.location.href = data.authorization_url
    },
    onError: (err: Error) => {
      setFeedback(`OAuth Error: ${err.message}`)
    },
  })

  // Disconnect Mailbox mutation
  const disconnectMutation = useMutation({
    mutationFn: () => apiClient<LifecycleActionResponse>('/api/settings/disconnect', { method: 'POST' }),
    onSuccess: (data) => {
      setFeedback(data.message)
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
    onError: (err: Error) => {
      setFeedback(`Disconnect Error: ${err.message}`)
    },
  })

  // Purge All Data mutation
  const purgeMutation = useMutation({
    mutationFn: () => apiClient<LifecycleActionResponse>('/api/settings/purge', { method: 'POST' }),
    onSuccess: (data) => {
      setFeedback(data.message)
      setIsConfirmingPurge(false)
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      queryClient.invalidateQueries({ queryKey: ['opportunities'] })
    },
    onError: (err: Error) => {
      setFeedback(`Purge Error: ${err.message}`)
    },
  })

  if (isLoading || !settings) {
    return <div className="py-12 text-center text-slate-500 text-sm">Loading settings...</div>
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
          <SettingsIcon className="w-5 h-5 text-indigo-400" />
          Settings & Mailbox Lifecycle
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Manage your Gmail connection, AI extraction engine, and database retention policies
        </p>
      </div>

      {feedback && (
        <div className="rounded-xl bg-indigo-500/10 border border-indigo-500/20 p-4 text-xs text-indigo-300 flex items-center justify-between">
          <span>{feedback}</span>
          <button
            onClick={() => setFeedback(null)}
            className="text-indigo-400 hover:text-white ml-3 font-semibold cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* 1. Gmail Connection Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg space-y-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400 font-bold shrink-0">
              <Mail className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">Gmail Integration</h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Official Google OAuth 2.0 with strictly read-only Gmail scope
              </p>
            </div>
          </div>

          <span
            className={`text-xs px-2.5 py-1 rounded-full font-semibold border ${
              settings.has_google_credentials
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
            }`}
          >
            {settings.has_google_credentials ? 'Live Gmail Connected' : 'Synthetic Demo Mode'}
          </span>
        </div>

        <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 text-xs space-y-2">
          <div className="flex justify-between">
            <span className="text-slate-400">Connected Account:</span>
            <span className="font-mono text-slate-200">
              {settings.mailbox_email || 'demo.owner@relayn.local'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Sync Status:</span>
            <span className="capitalize text-slate-200 font-medium">{settings.sync_status}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Granted Scopes:</span>
            <span className="font-mono text-slate-300">gmail.readonly (Strictly Read-Only)</span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 pt-2">
          {!settings.has_google_credentials ? (
            <button
              onClick={() => connectGoogleMutation.mutate()}
              disabled={connectGoogleMutation.isPending}
              className="inline-flex items-center px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold transition cursor-pointer shadow"
            >
              <Mail className="w-4 h-4 mr-2" /> Connect Real Gmail Account
            </button>
          ) : (
            <button
              onClick={() => disconnectMutation.mutate()}
              disabled={disconnectMutation.isPending}
              className="inline-flex items-center px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold transition cursor-pointer"
            >
              <Unlink className="w-4 h-4 mr-2" /> Disconnect Mailbox
            </button>
          )}
        </div>
      </div>

      {/* 2. AI Extraction Engine Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 font-bold shrink-0">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">AI Extraction Agent</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Powered by Pydantic AI with self-healing validation retries
            </p>
          </div>
        </div>

        <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 text-xs space-y-2">
          <div className="flex justify-between">
            <span className="text-slate-400">Framework:</span>
            <span className="text-indigo-400 font-semibold font-mono">Pydantic AI (v2.66.0)</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Primary Model:</span>
            <span className="text-slate-200 font-mono">google:gemini-2.5-flash</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Resilience Mode:</span>
            <span className="text-emerald-400 font-medium">Automatic offline fixture fallback enabled</span>
          </div>
        </div>
      </div>

      {/* 3. Data Purge & Danger Zone */}
      <div className="bg-slate-900 border border-rose-900/30 rounded-xl p-6 shadow-lg space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 font-bold shrink-0">
            <Trash2 className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Danger Zone: Data Purge</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Wipe all imported emails and pipeline records while preserving your master password
            </p>
          </div>
        </div>

        <div className="bg-rose-500/5 border border-rose-500/10 rounded-lg p-4 text-xs text-rose-300">
          Purging will permanently delete all opportunities, SWE interview rounds, follow-ups, and raw emails.
          Active background jobs will be immediately canceled via generation fencing.
        </div>

        <div>
          {!isConfirmingPurge ? (
            <button
              onClick={() => setIsConfirmingPurge(true)}
              className="inline-flex items-center px-4 py-2 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 rounded-lg text-xs font-semibold transition cursor-pointer"
            >
              <Trash2 className="w-4 h-4 mr-2" /> Purge All Career Data
            </button>
          ) : (
            <div className="flex items-center gap-3">
              <button
                onClick={() => purgeMutation.mutate()}
                disabled={purgeMutation.isPending}
                className="inline-flex items-center px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-bold transition cursor-pointer shadow"
              >
                Yes, Purge Everything Now
              </button>
              <button
                onClick={() => setIsConfirmingPurge(false)}
                className="inline-flex items-center px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium transition cursor-pointer"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
