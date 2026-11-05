import { useQuery } from '@tanstack/react-query'
import { LayoutDashboard, Briefcase, Video, Award, Clock } from 'lucide-react'
import { apiClient } from '../../lib/api'
import type { OpportunitySummary } from '../../types/career'
import { PipelineAnalyticsDashboard } from './pipeline-analytics-dashboard'
import { SyncControlPanel } from '../sync/sync-control-panel'

export function DashboardPage() {
  const { data: opportunities = [], isLoading } = useQuery<OpportunitySummary[]>({
    queryKey: ['opportunities'],
    queryFn: () => apiClient<OpportunitySummary[]>('/api/career/opportunities'),
    refetchInterval: 6000,
  })

  const total = opportunities.length
  const activeCount = opportunities.filter((o) => !['rejected', 'withdrawn'].includes(o.status)).length
  const interviewsCount = opportunities.filter((o) =>
    ['screening', 'assessment', 'interviewing'].includes(o.status)
  ).length
  const offersCount = opportunities.filter((o) => o.status === 'offer').length
  const totalTasks = opportunities.reduce((acc, o) => acc + o.pending_follow_ups_count, 0)

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <LayoutDashboard className="w-5 h-5 text-indigo-400" />
            Executive Career Dashboard
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            High-level metrics, conversion rates, and true Sankey diagram flow of your job search
          </p>
        </div>
      </div>

      {/* Sync Control */}
      <SyncControlPanel />

      {/* High-level KPI Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl shadow">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Total Tracked</span>
            <Briefcase className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-1">{total}</div>
          <div className="text-[11px] text-indigo-400 font-medium mt-0.5">{activeCount} active pipeline</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl shadow">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Active Rounds</span>
            <Video className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-cyan-400 mt-1">{interviewsCount}</div>
          <div className="text-[11px] text-slate-400 mt-0.5">Screening & System Design</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl shadow">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Offers Received</span>
            <Award className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">{offersCount}</div>
          <div className="text-[11px] text-emerald-400 font-medium mt-0.5">
            {total > 0 ? Math.round((offersCount / total) * 100) : 0}% win rate
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl shadow">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Actionable Items</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400 mt-1">{totalTasks}</div>
          <div className="text-[11px] text-amber-400/90 font-medium mt-0.5">Pending follow-ups</div>
        </div>
      </div>

      {isLoading && (
        <div className="py-12 text-center text-slate-500 text-sm">Loading dashboard charts...</div>
      )}

      {/* Dedicated Visual Charts & Sankey Diagram */}
      {!isLoading && opportunities.length > 0 && (
        <PipelineAnalyticsDashboard opportunities={opportunities} />
      )}
    </div>
  )
}
