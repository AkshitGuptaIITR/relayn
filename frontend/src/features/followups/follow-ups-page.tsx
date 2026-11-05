import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckSquare, Clock } from 'lucide-react'
import { apiClient } from '../../lib/api'
import type { OpportunitySummary, OpportunityDetail } from '../../types/career'

export function FollowUpsPage() {
  // Load opportunities to pull all follow-up tasks
  const { data: opportunities = [] } = useQuery<OpportunitySummary[]>({
    queryKey: ['opportunities'],
    queryFn: () => apiClient<OpportunitySummary[]>('/api/career/opportunities'),
  })

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
          <CheckSquare className="w-5 h-5 text-indigo-400" />
          Software Engineering Follow-ups & To-Dos
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Pending availability replies, take-home challenge deadlines, and offer response actions
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {opportunities.map((opp) => (
          <OpportunityTaskCard key={opp.id} opportunityId={opp.id} companyName={opp.company_name} roleTitle={opp.role_title} />
        ))}
      </div>
    </div>
  )
}

function OpportunityTaskCard({
  opportunityId,
  companyName,
  roleTitle,
}: {
  opportunityId: string
  companyName: string
  roleTitle: string
}) {
  const queryClient = useQueryClient()

  const { data: opp } = useQuery<OpportunityDetail>({
    queryKey: ['opportunity', opportunityId],
    queryFn: () => apiClient<OpportunityDetail>(`/api/career/opportunities/${opportunityId}`),
  })

  const resolveMutation = useMutation({
    mutationFn: ({ taskId }: { taskId: string }) =>
      apiClient(`/api/career/follow-ups/${taskId}/resolve?action=completed`, { method: 'POST' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['opportunity', opportunityId] })
      queryClient.invalidateQueries({ queryKey: ['opportunities'] })
    },
  })

  const pendingTasks = opp?.follow_ups.filter((f) => f.status === 'pending') || []

  if (pendingTasks.length === 0) return null

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-3">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
        <div>
          <h4 className="text-sm font-semibold text-white">{companyName}</h4>
          <p className="text-xs text-slate-400">{roleTitle}</p>
        </div>
        <span className="text-[10px] bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2 py-0.5 rounded font-bold uppercase">
          {pendingTasks.length} Pending
        </span>
      </div>

      <div className="space-y-2">
        {pendingTasks.map((t) => (
          <div
            key={t.id}
            className="bg-slate-950 border border-slate-800 rounded-lg p-3 flex items-start justify-between gap-3 text-xs"
          >
            <div>
              <div className="font-semibold text-slate-200">{t.title}</div>
              {t.description && <p className="text-slate-400 mt-0.5">{t.description}</p>}
              <div className="text-[11px] text-amber-400/90 font-mono mt-1 flex items-center">
                <Clock className="w-3 h-3 mr-1" />
                Due: {t.due_date}
              </div>
            </div>

            <button
              onClick={() => resolveMutation.mutate({ taskId: t.id })}
              className="px-2.5 py-1 bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/30 border border-emerald-500/30 rounded text-xs font-medium transition cursor-pointer shrink-0"
            >
              Done
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
