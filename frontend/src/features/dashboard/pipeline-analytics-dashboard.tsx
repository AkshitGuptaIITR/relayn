import { useMemo } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { TrendingUp, GitFork } from 'lucide-react'
import type { OpportunitySummary } from '../../types/career'
import { TrueSankeyDiagram } from './true-sankey-diagram'

interface Props {
  opportunities: OpportunitySummary[]
}

const STAGE_ORDER = [
  { key: 'applied', label: 'Applied', color: '#6366f1' },
  { key: 'lead', label: 'Recruiter Lead', color: '#3b82f6' },
  { key: 'screening', label: 'Screening', color: '#a855f7' },
  { key: 'assessment', label: 'Take-home / OA', color: '#f59e0b' },
  { key: 'interviewing', label: 'Interview Rounds', color: '#06b6d4' },
  { key: 'offer', label: 'Offer Received', color: '#10b981' },
  { key: 'rejected', label: 'Rejected', color: '#64748b' },
]

export function PipelineAnalyticsDashboard({ opportunities }: Props) {
  // 1. Stage Funnel Calculation
  const funnelData = useMemo(() => {
    const counts: Record<string, number> = {}
    opportunities.forEach((o) => {
      counts[o.status] = (counts[o.status] || 0) + 1
    })

    return STAGE_ORDER.map((stage) => ({
      name: stage.label,
      count: counts[stage.key] || 0,
      color: stage.color,
    }))
  }, [opportunities])

  // 2. Conversion Flow / Sankey-style Breakdown
  const total = opportunities.length
  const interviewsCount = opportunities.filter((o) => ['screening', 'assessment', 'interviewing'].includes(o.status)).length
  const offersCount = opportunities.filter((o) => o.status === 'offer').length

  const conversionRate = total > 0 ? Math.round((offersCount / total) * 100) : 0
  const interviewRate = total > 0 ? Math.round((interviewsCount / total) * 100) : 0

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-indigo-400" />
            Software Engineering Pipeline Funnel & Analytics
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Visualizing progression from Application & Outreach to Technical Rounds and Formal Offers
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="bg-slate-950 border border-slate-800 px-3 py-1.5 rounded-lg text-xs">
            <span className="text-slate-400 mr-1.5">Interview Rate:</span>
            <span className="text-cyan-400 font-bold">{interviewRate}%</span>
          </div>
          <div className="bg-slate-950 border border-slate-800 px-3 py-1.5 rounded-lg text-xs">
            <span className="text-slate-400 mr-1.5">Offer Rate:</span>
            <span className="text-emerald-400 font-bold">{conversionRate}%</span>
          </div>
        </div>
      </div>

      {/* True D3 Sankey Diagram */}
      <div className="bg-slate-950 border border-slate-800 rounded-xl p-4">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
          <GitFork className="w-4 h-4 text-indigo-400 rotate-90" />
          True Sankey Diagram (Application-to-Offer Flow)
        </div>
        <p className="text-[11px] text-slate-500 mb-4">
          Width of bands represents proportional volume of opportunities flowing between stages.
        </p>

        <TrueSankeyDiagram opportunities={opportunities} />
      </div>

      {/* Recharts Stage Distribution Chart */}
      <div className="bg-slate-950 border border-slate-800 rounded-xl p-4">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
          Opportunity Count by Stage
        </div>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={funnelData} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
              <XAxis type="number" stroke="#64748b" fontSize={11} allowDecimals={false} />
              <YAxis dataKey="name" type="category" stroke="#94a3b8" fontSize={11} width={110} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
              />
              <Bar dataKey="count" radius={[0, 6, 6, 0]}>
                {funnelData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
