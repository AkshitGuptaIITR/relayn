# Relayn AI Agent Architecture & Operational Specification

This document details the engineering specifications of the autonomous career management agent powering **Relayn**, its underlying Pydantic AI framework, and its operational guardrails.

---

## 1. Agent Objective & Scope

The Relayn Agent operates as an autonomous background intelligence layer. Its primary mandate is to:
1. Ingest asynchronous raw email communications via read-only Gmail API integration.
2. Filter non-career communications (newsletters, receipts, marketing).
3. Extract high-dimensional structured entities (companies, roles, stages, recruiter contacts, technical interview rounds, take-home deadlines, compensation).
4. Propose transactional changes to an existing relational career pipeline while strictly preserving data provenance.

---

## 2. Pydantic AI Agent Implementation

Relayn leverages **Pydantic AI** (`pydantic-ai`) backed by Google Gemini (`gemini-3.8-flash`).

### Agent System Prompt Design:
```text
You are an expert AI Career Relationship Agent.
Analyze the provided email and extract structured career management insights according to the schema.

Rules:
1. Determine if this email is directly related to a job application, recruiter outreach, interview, technical test, offer, or rejection.
2. If it is NOT career related (e.g. newsletter, product marketing, order confirmation, spam), set is_career_related=false.
3. If it IS career related:
   - Identify company_name and clean domain.
   - Identify role_title.
   - Determine opportunity_type: 'application' or 'lead'.
   - Determine current_stage: 'lead', 'applied', 'screening', 'assessment', 'interviewing', 'offer', 'rejected', or 'withdrawn'.
   - Categorize software engineering interview rounds if applicable: 'recruiter_screen', 'technical_screen', 'coding_dsa', 'system_design', 'take_home_review', 'hiring_manager', 'behavioral', or 'onsite_loop'.
   - Extract meeting links (Google Meet, Zoom) and preparation notes into milestones.
   - Extract actionable candidate follow-up tasks into follow_ups.
   - Extract exact evidence quotes from the body.
   - If ambiguous, set requires_human_review=true and explain in review_reason.
```

### Self-Healing Validation Loops:
- Pydantic AI executes with `retries=2`.
- When the LLM outputs malformed dates or schema violations, Pydantic AI intercepts the `ValidationError`, appends the exact error message back into the model's conversation history, and requests an immediate correction.

---

## 3. The Extraction & Decision Schema

All extractions adhere to the typed `EmailExtractionResult` contract:

```python
class EmailExtractionResult(BaseModel):
    is_career_related: bool
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    company_name: str | None = None
    company_domain: str | None = None
    role_title: str | None = None
    opportunity_type: Literal["application", "lead"] = "application"
    current_stage: OpportunityStage | None = None
    event_type: EventType | None = None
    event_summary: str | None = None
    evidence_quote: str | None = None
    salary_text: str | None = None
    location: str | None = None
    contacts: list[ExtractedContact] = []
    milestones: list[ExtractedMilestone] = []
    follow_ups: list[ExtractedFollowUp] = []
    requires_human_review: bool = False
    review_reason: str | None = None
```

---

## 4. Software Engineering Interview Taxonomy

The agent understands the nuanced hierarchy of software engineering interview loops:

| Stage Identifier | Interview Round Name | Extracted Entities |
|---|---|---|
| `recruiter_screen` | Recruiter Phone Screen | Recruiter Name, Phone/Video link, Availability questions |
| `technical_screen` | Technical Phone Screen | Coding platform, live LeetCode/DSA expectations |
| `coding_dsa` | DSA & Algorithms Round | Data structures, time complexity focus |
| `system_design` | Systems & Architecture Round | Scalability, database sharding, microservices prep notes |
| `take_home_review` | Take-Home Codebase Review | GitHub repositories, submission deadlines |
| `hiring_manager` | Engineering Manager Chat | Team fit, past projects, leadership principles |
| `behavioral` | Values & Culture Round | STAR method storytelling, company values |
| `onsite_loop` | Virtual / Onsite Panel | Multi-interviewer schedule, agenda |

---

## 5. Resilience & Graceful Fallback Strategy

To safeguard against external API outages, rate limits, and network failures:
1. **Raw Email Persistence First**: Messages are stored in `email_messages` and committed *before* agent extraction is invoked.
2. **Quota & Outage Circuit Breaker**:
   - If Gemini returns `429 RESOURCE_EXHAUSTED` (e.g. Free Tier quotas) or `503 UNAVAILABLE`:
   - The provider catches the exception, logs a structured warning, and routes the message through the local **Deterministic Fixture Extractor**.
   - No background jobs fail, and no emails are dropped.
3. **Optimistic Concurrency & Monotonic Ranking**:
   - Record versioning (`record_version`) prevents stale worker writes.
   - Status updates only advance monotonically along the hiring funnel; late-arriving acknowledgment emails cannot overwrite an ongoing interview loop or job offer.
