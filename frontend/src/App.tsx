import { useEffect, useState } from 'react'

interface HealthResponse {
  status: string
  app: string
  version: string
}

export function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/health')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data: HealthResponse) => {
        setHealth(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-6">
      <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-2xl text-center">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-lg bg-indigo-600/20 text-indigo-400 mb-4 font-bold text-xl">
          R
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-white mb-2">Relayn</h1>
        <p className="text-sm text-slate-400 mb-6">Your job search, on autopilot.</p>

        <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 text-left">
          <div className="text-xs uppercase tracking-wider text-slate-400 mb-2 font-semibold">
            Backend API Link Status
          </div>
          {loading && <p className="text-sm text-slate-400">Connecting to backend...</p>}
          {error && (
            <p className="text-sm text-rose-400">
              Connection failed: {error}. Make sure FastAPI is running on port 8000.
            </p>
          )}
          {health && (
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Status:</span>
                <span className="text-emerald-400 font-medium">{health.status}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Application:</span>
                <span className="text-slate-200">{health.app}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Version:</span>
                <span className="text-slate-200">{health.version}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
