export interface Contact {
  id: string
  name: string
  email: string
  role?: string | null
  linkedin_url?: string | null
}

export type InterviewRoundCategory =
  | 'recruiter_screen'
  | 'technical_screen'
  | 'coding_dsa'
  | 'system_design'
  | 'take_home_review'
  | 'hiring_manager'
  | 'behavioral'
  | 'onsite_loop'

export interface Milestone {
  id: string
  title: string
  milestone_type: 'interview' | 'technical_assessment' | 'deadline' | 'offer_response'
  round_category?: InterviewRoundCategory | null
  round_number?: number | null
  meeting_url?: string | null
  prep_notes?: string | null
  scheduled_at?: string | null
  scheduled_date?: string | null
  is_time_uncertain: boolean
  status: string
}

export interface FollowUpTask {
  id: string
  title: string
  description?: string | null
  due_date: string
  status: 'pending' | 'completed' | 'dismissed'
}

export interface OpportunityEvent {
  id: string
  event_type: string
  summary: string
  occurred_at: string
  email_message_id?: string | null
}

export interface OpportunitySummary {
  id: string
  company_name: string
  company_domain?: string | null
  role_title: string
  opportunity_type: 'application' | 'lead'
  status: 'lead' | 'applied' | 'screening' | 'interviewing' | 'assessment' | 'offer' | 'rejected' | 'withdrawn'
  salary_text?: string | null
  location?: string | null
  last_activity_at: string
  pending_follow_ups_count: number
  upcoming_interviews_count: number
}

export interface OpportunityDetail {
  id: string
  company_name: string
  company_domain?: string | null
  role_title: string
  opportunity_type: 'application' | 'lead'
  status: 'lead' | 'applied' | 'screening' | 'interviewing' | 'assessment' | 'offer' | 'rejected' | 'withdrawn'
  salary_text?: string | null
  location?: string | null
  notes?: string | null
  created_at: string
  updated_at: string
  contacts: Contact[]
  milestones: Milestone[]
  follow_ups: FollowUpTask[]
  events: OpportunityEvent[]
}

export interface ReviewProposal {
  id: string
  email_message_id: string
  opportunity_id?: string | null
  proposal_type: string
  proposed_changes: Record<string, any>
  status: 'pending' | 'accepted' | 'dismissed'
  created_at: string
}
