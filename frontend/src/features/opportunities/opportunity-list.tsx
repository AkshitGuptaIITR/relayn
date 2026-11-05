import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Briefcase,
  ChevronRight,
  Clock,
  DollarSign,
  MapPin,
  Video,
} from 'lucide-react'
import { apiClient } from '../../lib/api'
import type { OpportunitySummary } from '../../types/career'

const STAGE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  lead: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/20' },
  applied: { bg: 'bg-indigo-500/10', text: 'text-indigo-400', border: 'border-indigo-500/20' },
  screening: { bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/20' },
  assessment: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/20' },
  interviewing: { bg: 'bg-cyan-500/10', text: 'text-cyan-400', border: 'border-cyan-500/20' },
  offer: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20' },
  rejected: { bg: 'bg-slate-500/10', text: 'text-slate-400', border: 'border-slate-500/20' },
  withdrawn: { bg: 'bg-rose-500/10', text: 'text-rose-400', border: 'border-rose-500/20' },
}

interface Props {
  onSelectOpportunity: (id: string) => void
}

export function OpportunityList({ onSelectOpportunity }: Props) {
  const [filter, setFilter] = useState<string>('all')

  const { data: opportunities = [], isLoading } = useQuery<OpportunitySummary[]>({
    queryKey: ['opportunities'],
    queryFn: () => apiClient<OpportunitySummary[]>('/api/career/opportunities'),
    refetchInterval: 6000,
  })

  const filtered = opportunities.filter((opp) => {
    if (filter === 'all') return true
    if (filter === 'active') return !['rejected', 'withdrawn'].includes(opp.status)
    if (filter === 'interviews') return ['screening', 'assessment', 'interviewing'].includes(opp.status)
    if (filter === 'offers') return opp.status === 'offer'
    return opp.status === filter
  })

  return (
    <div className="space-y-4">
      {/* Filters Toolbar */}
      <div className="flex flex-wrap items-center gap-2 pb-2">
        {['all', 'active', 'interviews', 'offers', 'rejected'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition cursor-pointer ${
              filter === f
                ? 'bg-indigo-600 text-white shadow'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            {f} {f === 'all' && `(${opportunities.length})`}
          </button>
        ))}
      </div>

      {isLoading && (
        <div className="py-12 text-center text-slate-500 text-sm">
          Loading software engineering pipeline...
        </div>
      )}

      {!isLoading && filtered.length === 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-8 text-center text-slate-400">
          <Briefcase className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p className="text-sm">No software engineering opportunities match this filter.</p>
        </div>
      )}

      {/* Grid of Opportunity Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((opp) => {
          const badge = STAGE_COLORS[opp.status] || STAGE_COLORS.applied

          return (
            <div
              key={opp.id}
              onClick={() => onSelectOpportunity(opp.id)}
              className="bg-slate-900 border border-slate-800 hover:border-indigo-500/50 rounded-xl p-5 shadow-md hover:shadow-indigo-500/5 transition cursor-pointer flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-center text-indigo-400 font-bold shrink-0">
                      {opp.company_name.charAt(0)}
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-white group-hover:text-indigo-400 transition leading-tight">
                        {opp.company_name}
                      </h4>
                      <p className="text-xs text-slate-400 font-mono mt-0.5 truncate max-w-[180px]">
                        {opp.company_domain || 'company.com'}
                      </p>
                    </div>
                  </div>

                  <span
                    className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full border ${badge.bg} ${badge.text} ${badge.border}`}
                  >
                    {opp.status}
                  </span>
                </div>

                <div className="font-medium text-slate-100 text-sm mb-3">
                  {opp.role_title}
                </div>

                <div className="space-y-1.5 text-xs text-slate-400 mb-4">
                  {opp.salary_text && (
                    <div className="flex items-center text-emerald-400 font-medium">
                      <DollarSign className="w-3.5 h-3.5 mr-1 shrink-0" />
                      <span>{opp.salary_text}</span>
                    </div>
                  )}
                  {opp.location && (
                    <div className="flex items-center">
                      <MapPin className="w-3.5 h-3.5 mr-1 shrink-0 text-slate-500" />
                      <span>{opp.location}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Card Footer */}
              <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500">
                <div className="flex items-center gap-3">
                  {opp.upcoming_interviews_count > 0 && (
                    <span className="flex items-center text-cyan-400 font-medium">
                      <Video className="w-3.5 h-3.5 mr-1" />
                      {opp.upcoming_interviews_count} round{opp.upcoming_interviews_count > 1 ? 's' : ''}
                    </span>
                  )}
                  {opp.pending_follow_ups_count > 0 && (
                    <span className="flex items-center text-amber-400 font-medium">
                      <Clock className="w-3.5 h-3.5 mr-1" />
                      {opp.pending_follow_ups_count} task{opp.pending_follow_ups_count > 1 ? 's' : ''}
                    </span>
                  )}
                </div>

                <div className="flex items-center text-indigo-400 text-xs font-semibold group-hover:translate-x-0.5 transition">
                  Details <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
