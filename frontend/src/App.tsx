import { useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './app/auth-context'
import { LoginPage } from './features/auth/login-page'
import { AppLayout } from './app/app-layout'
import { ProtectedRoute } from './app/protected-route'
import { SyncControlPanel } from './features/sync/sync-control-panel'
import { OpportunityList } from './features/opportunities/opportunity-list'
import { OpportunityDetailView } from './features/opportunities/opportunity-detail'
import { ReviewQueuePage } from './features/review/review-queue-page'
import { FollowUpsPage } from './features/followups/follow-ups-page'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function OpportunitiesPage() {
  const [selectedOppId, setSelectedOppId] = useState<string | null>(null)

  if (selectedOppId) {
    return (
      <OpportunityDetailView
        opportunityId={selectedOppId}
        onBack={() => setSelectedOppId(null)}
      />
    )
  }

  return (
    <div className="space-y-6">
      <SyncControlPanel />

      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Software Engineering Pipeline</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Active applications, recruiter leads, take-homes, and interview rounds
          </p>
        </div>
      </div>

      <OpportunityList onSelectOpportunity={(id) => setSelectedOppId(id)} />
    </div>
  )
}

function ContactsPage() {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold text-white">Recruiters & Contacts</h2>
      <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-8 text-center text-slate-400">
        <p className="text-sm">No recruiter contacts discovered yet.</p>
      </div>
    </div>
  )
}

function SettingsPage() {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold text-white">Settings & Integration</h2>
      <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 space-y-4 max-w-xl">
        <div>
          <h3 className="text-sm font-semibold text-slate-200">Gmail Connection</h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Connect your mailbox via read-only OAuth or enable Synthetic Demo mode.
          </p>
        </div>
      </div>
    </div>
  )
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                <Route path="/" element={<OpportunitiesPage />} />
                <Route path="/review" element={<ReviewQueuePage />} />
                <Route path="/follow-ups" element={<FollowUpsPage />} />
                <Route path="/contacts" element={<ContactsPage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
