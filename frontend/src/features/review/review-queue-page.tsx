import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { FileCheck2, Check, X, HelpCircle } from 'lucide-react'
import { apiClient } from '../../lib/api'
import type { ReviewProposal } from '../../types/career'

export function ReviewQueuePage() {
  const queryClient = useQueryClient()

  const { data: proposals = [], isLoading } = useQuery<ReviewProposal[]>({
    queryKey: ['review-proposals'],
    queryFn: () => apiClient<ReviewProposal[]>('/api/career/review-proposals'),
    refetchInterval: 5000,
  })

  const resolveMutation = useMutation({
    mutationFn: ({ proposalId, action }: { proposalId: string; action: 'accepted' | 'dismissed' }) =>
      apiClient(`/api/career/review-proposals/${proposalId}/resolve?action=${action}`, {
        method: 'POST',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-proposals'] })
      queryClient.invalidateQueries({ queryKey: ['opportunities'] })
    },
  })

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <FileCheck2 className="w-5 h-5 text-indigo-400" />
            Human Review Queue
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Review ambiguous extractions, role classifications, or uncertain status transitions
          </p>
        </div>

        <span className="text-xs bg-indigo-500/10 text-indigo-400 font-semibold px-2.5 py-1 rounded-full border border-indigo-500/20">
          {proposals.length} Pending
        </span>
      </div>

      {isLoading && (
        <div className="py-12 text-center text-slate-500 text-sm">
          Loading proposals...
        </div>
      )}

      {!isLoading && proposals.length === 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-12 text-center text-slate-400">
          <Check className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
          <h3 className="text-sm font-semibold text-white">All caught up!</h3>
          <p className="text-xs text-slate-500 mt-1">
            There are no ambiguous opportunities or extractions requiring human confirmation.
          </p>
        </div>
      )}

      <div className="space-y-4">
        {proposals.map((proposal) => {
          const changes = proposal.proposed_changes

          return (
            <div
              key={proposal.id}
              className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 font-bold shrink-0">
                    <HelpCircle className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-white">
                      {changes.company_name || 'Proposed Opportunity'}
                    </h4>
                    <p className="text-xs text-amber-400/90 font-medium mt-0.5">
                      {proposal.proposal_type.replace(/_/g, ' ')}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() =>
                      resolveMutation.mutate({ proposalId: proposal.id, action: 'accepted' })
                    }
                    className="inline-flex items-center px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition cursor-pointer shadow"
                  >
                    <Check className="w-3.5 h-3.5 mr-1" /> Accept
                  </button>
                  <button
                    onClick={() =>
                      resolveMutation.mutate({ proposalId: proposal.id, action: 'dismissed' })
                    }
                    className="inline-flex items-center px-3 py-1.5 bg-slate-800 hover:bg-rose-500/20 text-slate-300 hover:text-rose-400 border border-slate-700 hover:border-rose-500/30 rounded-lg text-xs font-semibold transition cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5 mr-1" /> Dismiss
                  </button>
                </div>
              </div>

              {/* Proposed Details */}
              <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs space-y-1.5">
                <div className="text-slate-400">
                  <span className="font-semibold text-slate-300">Proposed Role:</span>{' '}
                  {changes.role_title || 'Software Engineer'}
                </div>
                <div className="text-slate-400">
                  <span className="font-semibold text-slate-300">Proposed Stage:</span>{' '}
                  <span className="capitalize text-indigo-400 font-medium">
                    {changes.stage || 'Applied'}
                  </span>
                </div>
                {changes.reason && (
                  <div className="text-slate-400 pt-1 border-t border-slate-800/80">
                    <span className="font-semibold text-slate-300">Review Note:</span>{' '}
                    {changes.reason}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
