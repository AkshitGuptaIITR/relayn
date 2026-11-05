import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  Building2,
  Calendar,
  Clock,
  Code2,
  Cpu,
  DollarSign,
  ExternalLink,
  Mail,
  MapPin,
  MessageSquare,
  User,
  Video,
} from 'lucide-react'
import { apiClient } from '../../lib/api'
import type { OpportunityDetail } from '../../types/career'

const ROUND_CATEGORY_LABELS: Record<string, { label: string; icon: any; color: string }> = {
  recruiter_screen: { label: 'Recruiter Phone Screen', icon: MessageSquare, color: 'text-purple-400 bg-purple-500/10 border-purple-500/20' },
  technical_screen: { label: 'Technical Phone Screen', icon: Code2, color: 'text-blue-400 bg-blue-500/10 border-blue-500/20' },
  coding_dsa: { label: 'Data Structures & Algorithms', icon: Code2, color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20' },
  system_design: { label: 'Distributed Systems & Architecture', icon: Cpu, color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20' },
  take_home_review: { label: 'Take-home Assignment Review', icon: Code2, color: 'text-amber-400 bg-amber-500/10 border-amber-500/20' },
  hiring_manager: { label: 'Hiring Manager Round', icon: User, color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' },
  behavioral: { label: 'Values & Behavioral', icon: User, color: 'text-rose-400 bg-rose-500/10 border-rose-500/20' },
  onsite_loop: { label: 'Full Onsite / Virtual Panel Loop', icon: Building2, color: 'text-fuchsia-400 bg-fuchsia-500/10 border-fuchsia-500/20' },
}

interface Props {
  opportunityId: string
  onBack: () => void
}

export function OpportunityDetailView({ opportunityId, onBack }: Props) {
  const queryClient = useQueryClient()

  const { data: opp, isLoading } = useQuery<OpportunityDetail>({
    queryKey: ['opportunity', opportunityId],
    queryFn: () => apiClient<OpportunityDetail>(`/api/career/opportunities/${opportunityId}`),
  })

  const resolveTaskMutation = useMutation({
    mutationFn: ({ taskId, action }: { taskId: string; action: string }) =>
      apiClient(`/api/career/follow-ups/${taskId}/resolve?action=${action}`, { method: 'POST' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['opportunity', opportunityId] })
      queryClient.invalidateQueries({ queryKey: ['opportunities'] })
    },
  })

  if (isLoading || !opp) {
    return (
      <div className="py-16 text-center text-slate-500 text-sm">
        Loading engineering opportunity details...
      </div>
    )
  }

  // Filter out SWE interview rounds vs deadlines
  const interviewRounds = opp.milestones.filter((m) => m.milestone_type === 'interview')
  const assessmentsAndDeadlines = opp.milestones.filter((m) => m.milestone_type !== 'interview')

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header Bar */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="inline-flex items-center text-xs font-semibold text-slate-400 hover:text-white transition cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4 mr-1.5" /> Back to Pipeline
        </button>

        <span className="text-xs uppercase font-bold tracking-wider px-3 py-1 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-indigo-400">
          Stage: {opp.status}
        </span>
      </div>

      {/* Main Info Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-indigo-400 text-sm font-semibold mb-1">
              <Building2 className="w-4 h-4" />
              <span>{opp.company_name}</span>
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight">{opp.role_title}</h2>
            <p className="text-xs text-slate-400 mt-1">
              Type: <span className="capitalize font-medium text-slate-200">{opp.opportunity_type}</span>
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs">
            {opp.salary_text && (
              <div className="px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-semibold flex items-center">
                <DollarSign className="w-3.5 h-3.5 mr-1" />
                {opp.salary_text}
              </div>
            )}
            {opp.location && (
              <div className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 flex items-center">
                <MapPin className="w-3.5 h-3.5 mr-1 text-slate-400" />
                {opp.location}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Grid: Interview Rounds & Follow-ups */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* SWE Interview Rounds Section */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Video className="w-4 h-4 text-cyan-400" />
              Software Engineering Interview Rounds
            </h3>
            <span className="text-xs text-cyan-400 font-medium bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
              {interviewRounds.length} round{interviewRounds.length === 1 ? '' : 's'}
            </span>
          </div>

          {interviewRounds.length === 0 ? (
            <p className="text-xs text-slate-500 py-4 text-center">
              No interview rounds scheduled yet.
            </p>
          ) : (
            <div className="space-y-3">
              {interviewRounds.map((round) => {
                const categoryMeta =
                  (round.round_category && ROUND_CATEGORY_LABELS[round.round_category]) ||
                  ROUND_CATEGORY_LABELS.technical_screen

                const CategoryIcon = categoryMeta.icon

                return (
                  <div
                    key={round.id}
                    className="bg-slate-950 border border-slate-800/80 rounded-lg p-4 space-y-2.5"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="w-6 h-6 rounded-md bg-slate-900 border border-slate-800 flex items-center justify-center text-xs font-bold text-indigo-400">
                          {round.round_number || 1}
                        </span>
                        <div>
                          <div className="text-sm font-semibold text-white">{round.title}</div>
                          <span
                            className={`inline-flex items-center text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border mt-0.5 ${categoryMeta.color}`}
                          >
                            <CategoryIcon className="w-3 h-3 mr-1" />
                            {categoryMeta.label}
                          </span>
                        </div>
                      </div>

                      {round.scheduled_date && (
                        <div className="text-right text-xs">
                          <div className="text-slate-200 font-medium flex items-center justify-end">
                            <Calendar className="w-3.5 h-3.5 mr-1 text-slate-400" />
                            {round.scheduled_date}
                          </div>
                        </div>
                      )}
                    </div>

                    {round.prep_notes && (
                      <div className="text-xs bg-slate-900/60 p-2.5 rounded border border-slate-800 text-slate-300">
                        <span className="text-indigo-400 font-medium">Prep Focus: </span>
                        {round.prep_notes}
                      </div>
                    )}

                    {round.meeting_url && (
                      <div className="pt-1 flex items-center">
                        <a
                          href={round.meeting_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center text-xs text-cyan-400 hover:text-cyan-300 font-medium transition"
                        >
                          <Video className="w-3.5 h-3.5 mr-1.5" />
                          Join Interview Video Link
                          <ExternalLink className="w-3 h-3 ml-1" />
                        </a>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {/* Take-home & Assessments */}
          {assessmentsAndDeadlines.length > 0 && (
            <div className="pt-3 border-t border-slate-800 space-y-2">
              <h4 className="text-xs font-semibold text-amber-400 flex items-center gap-1.5">
                <Code2 className="w-3.5 h-3.5" />
                Technical Take-home & Deadlines
              </h4>
              {assessmentsAndDeadlines.map((a) => (
                <div
                  key={a.id}
                  className="bg-slate-950 p-2.5 rounded border border-slate-800 text-xs flex justify-between items-center"
                >
                  <span className="text-slate-200">{a.title}</span>
                  <span className="text-amber-400 font-mono">{a.scheduled_date}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Actionable Tasks & Recruiter Contacts Section */}
        <div className="space-y-6">
          {/* Follow-up Tasks */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-3">
              <Clock className="w-4 h-4 text-amber-400" />
              Actionable Follow-up Tasks
            </h3>

            {opp.follow_ups.length === 0 ? (
              <p className="text-xs text-slate-500 py-3 text-center">No pending tasks.</p>
            ) : (
              <div className="space-y-2.5">
                {opp.follow_ups.map((task) => (
                  <div
                    key={task.id}
                    className={`p-3 rounded-lg border flex items-start justify-between gap-3 text-xs ${
                      task.status === 'completed'
                        ? 'bg-slate-950/40 border-slate-800/40 text-slate-500 line-through'
                        : 'bg-slate-950 border-slate-800 text-slate-200'
                    }`}
                  >
                    <div>
                      <div className="font-semibold text-slate-100">{task.title}</div>
                      {task.description && (
                        <p className="text-slate-400 mt-0.5">{task.description}</p>
                      )}
                      <div className="text-[11px] text-amber-400/90 font-mono mt-1">
                        Due: {task.due_date}
                      </div>
                    </div>

                    {task.status === 'pending' && (
                      <button
                        onClick={() =>
                          resolveTaskMutation.mutate({ taskId: task.id, action: 'completed' })
                        }
                        className="px-2 py-1 bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/30 border border-emerald-500/30 rounded text-[11px] font-medium transition cursor-pointer shrink-0"
                      >
                        Complete
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recruiter & Contacts */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-3">
              <User className="w-4 h-4 text-indigo-400" />
              Recruiter & Hiring Contacts
            </h3>

            {opp.contacts.length === 0 ? (
              <p className="text-xs text-slate-500 py-2 text-center">
                No recruiter contact info extracted.
              </p>
            ) : (
              <div className="space-y-2">
                {opp.contacts.map((contact) => (
                  <div
                    key={contact.id}
                    className="bg-slate-950 border border-slate-800 p-3 rounded-lg flex items-center justify-between text-xs"
                  >
                    <div>
                      <div className="font-semibold text-slate-100">{contact.name}</div>
                      <div className="text-slate-400 font-mono flex items-center gap-1.5 mt-0.5">
                        <Mail className="w-3 h-3 text-slate-500" />
                        {contact.email}
                      </div>
                    </div>

                    <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400">
                      {contact.role || 'Recruiter'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Chronological Event History */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-3">
          <Calendar className="w-4 h-4 text-indigo-400" />
          Chronological Email Activity Timeline
        </h3>

        <div className="space-y-3">
          {opp.events.map((event) => (
            <div
              key={event.id}
              className="border-l-2 border-indigo-500/50 pl-4 py-1 text-xs space-y-1 relative"
            >
              <div className="absolute -left-[5px] top-2 w-2 h-2 rounded-full bg-indigo-500" />
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-200 capitalize">
                  {event.event_type.replace(/_/g, ' ')}
                </span>
                <span className="text-slate-500 font-mono">
                  {new Date(event.occurred_at).toLocaleDateString()}
                </span>
              </div>
              <p className="text-slate-400">{event.summary}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
