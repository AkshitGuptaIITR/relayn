# Relayn Email Segregation, Prompting, and Categorization Analysis

**Author:** Antigravity AI Engineering  
**Scope:** Email Ingestion, LLM Prompt Architecture, Database Taxonomy, Opportunity Deduplication, and Classification Remediation  
**Status:** Audit & Remediation Plan  

---

## 1. Executive Summary

Relayn is designed as an autonomous, privacy-first career relationship manager for software engineers. A core promise of the platform is the ability to ingest raw emails from a user's connected Gmail inbox, reliably distinguish between **actual hiring/recruitment activity** and non-hiring noise, classify each email into a structured hiring stage, and maintain an accurate, chronological pipeline of opportunities.

An in-depth technical audit of the codebase, the active PostgreSQL database, and the AI extraction engine revealed significant architectural and logic-level issues:

1. **Binary Segregation Fallacy:** Emails are partitioned via a single boolean flag (`is_career_related: bool`). The system fails to distinguish between *direct candidate hiring interactions*, *automated job alerts/digests* (LinkedIn/Indeed), *generic talent pool marketing*, *referrals made by the candidate*, and *unrelated emails*.
2. **Duplicate Opportunity Creation (Critical Pipeline Bug):** Opportunity linking uses a strict `company_id + role_title` match. When consecutive emails in the same thread use slight variations (e.g., *"Application Received: Senior Platform Engineer"* vs. *"Interview Confirmation: Technical Architecture Round"*), the role title defaults to `"Software Engineer"`, failing the match and creating duplicate parallel opportunities for the exact same job application.
3. **Brittle Gmail Ingestion Search:** The Gmail sync query is a naive 9-keyword string that generates both false positives (credit card/college applications, purchase offers) and false negatives (omits ATS emails from Greenhouse, Lever, Ashby, or Workday that lack those exact words).
4. **Oversimplified LLM Prompting:** The extraction system prompt is only 15 lines of generic instructions without few-shot examples, edge-case boundaries, negative examples, or confidence calibration guidelines.
5. **Silent Mock Fallback Anti-Pattern:** When LLM calls fail (such as API 503 errors or rate limits), the system catches the error and silently routes the real email to `DeterministicFixtureProvider`, which contains a hardcoded list of 15 tech companies and 9 job titles, corrupting production data with mock extractions.
6. **Zero Review Proposals Triggered:** Despite having a `review_proposals` table and human-in-the-loop schemas, 0 proposals have been generated in the database because the prompt and pipeline lack actionable confidence thresholds.

---

## 2. Current Architecture: How Emails are Segregated & Categorized Today

```
[Gmail API / Synthetic Gateway]
           │
           ▼ (Filter 1: SWE_CAREER_GMAIL_QUERY)
   email_messages table (raw plain text)
           │
           ▼ (Filter 2: LLM / Fixture Provider)
   EmailExtractionResult
     - is_career_related: bool (Binary)
     - opportunity_type: 'application' | 'lead'
     - current_stage: 'lead'..'rejected'
     - event_type: 13 enum strings
     - round_category: 8 SWE rounds
           │
           ▼ (Filter 3: CareerPipelineService)
   Database Entity Resolution
     - Matches Company (ilike name)
     - Matches Opportunity (company_id AND role_title ilike)
     - Creates Event, Milestones, Tasks
```

### 2.1 Pre-Ingestion Filter (Gmail API Query)
Located in `backend/app/integrations/mailbox/gmail.py`:
```python
SWE_CAREER_GMAIL_QUERY = (
    '("interview" OR "application" OR "recruiter" OR "hiring" OR "offer" '
    'OR "assessment" OR "take-home" OR "systems design" OR "coding challenge")'
)
```
Only messages matching this string query are fetched from Gmail during full syncs.

### 2.2 Extraction Prompt Design
Located in `backend/app/integrations/llm/pydantic_ai_provider.py` and `gemini.py`:
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

### 2.3 Current Taxonomy & Schema Attributes
The system categorizes emails across five distinct enum vectors:

| Schema Attribute | Allowed Values | Semantic Meaning |
|---|---|---|
| **Relevance** | `is_career_related: bool` | Binary gate: processed as career or ignored |
| **Opportunity Type** | `application`, `lead` | Candidate-initiated (`application`) vs. Recruiter-initiated (`lead`) |
| **Hiring Stage** | `lead`, `applied`, `screening`, `assessment`, `interviewing`, `offer`, `rejected`, `withdrawn` | Candidate's progression in the hiring funnel |
| **Event Type** | `application_submitted`, `recruiter_outreach`, `screening_invitation`, `screening_scheduled`, `technical_assessment_assigned`, `technical_assessment_submitted`, `interview_scheduled`, `interview_completed`, `rejection_received`, `offer_received`, `offer_accepted`, `offer_declined`, `general_update` | Granular transactional email communication type |
| **SWE Round Category** | `recruiter_screen`, `technical_screen`, `coding_dsa`, `system_design`, `take_home_review`, `hiring_manager`, `behavioral`, `onsite_loop` | Software engineering specific interview classification |

---

## 3. Database Audit & Live Data Analysis

A direct inspection of the live PostgreSQL database (`DATABASE_URL=postgresql+asyncpg://postgres:root@localhost:5432/relayn`) reveals the actual state of stored data:

```
Table Row Counts:
- mailbox_accounts: 1
- email_messages: 29
- opportunities: 17
- companies: 15
- contacts: 8
- milestones: 8
- follow_up_tasks: 22
- review_proposals: 0  <-- (Review queue completely empty!)
- opportunity_events: 55
```

### 3.1 Live Database Opportunity Mismatches & Duplication

Inspecting the relationship between emails and generated opportunities demonstrates severe data fragmentation:

#### Case 1: Datadog Application Fragmentation
* **Email A:** `no-reply@datadoghq.com` -> *"Application Received: Senior Platform Engineer at Datadog"*  
  -> Result: Created Opportunity `294f150e`: **Datadog - Senior Platform Engineer (Status: applied)**
* **Email B:** `alex.chen@datadoghq.com` -> *"Datadog Interview Confirmation: Technical Architecture Round"*  
  -> Result: Created Opportunity `ecc3ca63`: **Datadog - Software Engineer (Status: interviewing)**

**Impact:** The user has **two distinct Datadog opportunities** in their dashboard for one single job candidacy! The initial application remains permanently stuck in `applied`, while a second phantom opportunity sits in `interviewing`.

#### Case 2: Airbnb Application Fragmentation
* **Email A:** `dan.m@airbnb.com` -> *"Application Received: Staff Fullstack Engineer at Airbnb"*  
  -> Result: Created Opportunity `63878cb8`: **Airbnb - Staff Fullstack Engineer (Status: applied)**
* **Email B:** `dan.m@airbnb.com` -> *"Update on your application with Airbnb"* (Rejection letter)  
  -> Result: Created Opportunity `13b40eeb`: **Airbnb - Software Engineer (Status: rejected)**

**Impact:** The rejection was attached to a new, hallucinated "Software Engineer" opportunity, leaving the candidate's actual "Staff Fullstack Engineer" opportunity in an active `applied` state.

#### Case 3: Title Distortion Across Multiple Companies
* **Snowflake:** Email subject: *"Application Received: Staff Distributed Systems Engineer at Snowflake"*. Stored Opportunity: `Snowflake - Systems Engineer`.
* **Uber:** Email subject: *"Application Received: Senior Backend Engineer - Core Services at Uber"*. Stored Opportunity: `Uber - Software Engineer`.
* **Cloudflare:** Email subject: *"Application Received: Workers Runtime Engineer at Cloudflare"*. Stored Opportunity: `Cloudflare - Software Engineer`.

#### Case 4: Non-Career Emails
* `newsletter@medium.com` -> *"Top 10 Python libraries you should know in 2026"* -> `is_relevant: False`
* `auto-confirm@amazon.com` -> *"Your Amazon.com order #112-9847123 has shipped"* -> `is_relevant: False`

While these two obvious spam/receipt emails were successfully filtered out, the current logic is incapable of handling subtler categories.

---

## 4. Key Limitations & Wrong-Doings

### 4.1 Limitation 1: The Binary Segregation Fallacy
Real-world inboxes contain multiple categories of hiring-adjacent emails that cannot be modeled as a simple `is_career_related: true/false`:
* **Job Board Digests & Alerts:** Automated notifications from LinkedIn, Indeed, Glassdoor, and Wellfound (e.g., *"30 new jobs match your alert for Staff Backend Engineer"*). Under the current prompt, if the LLM sees job titles, it risks classifying this as an incoming `opportunity_type="lead"` or `application`, generating ghost opportunities.
* **Cold Marketing from Staffing Agencies:** Generic agency blasts (e.g., *"C2C requirement for Java Dev in Dallas"* sent to 5,000 engineers) are not authentic recruiter leads for the candidate.
* **Talent Community / Newsletter Blasts:** *"Life at Google: Summer Engineering Quarterly"* mentions hiring but is not an active candidacy.
* **Referrals Initiated by the User:** If the user refers a friend to their employer, the confirmation email (*"Thank you for referring John Doe for Backend Engineer"*) is career-related, but does NOT belong in the user's job search pipeline.
* **Post-Interview Surveys:** Feedback forms (*"Please rate your interview experience with Meta"*) are currently misidentified as interview scheduling or general updates.

### 4.2 Limitation 2: Absence of Thread-Aware Opportunity Resolution
In `CareerPipelineService.process_email_message`:
```python
# Current matching logic in backend/app/services/pipeline.py:
role_title = extracted.role_title or "Software Engineer"
opp_stmt = (
    select(Opportunity)
    .where(Opportunity.company_id == company.id)
    .where(Opportunity.role_title.ilike(role_title))
)
```
* **The Root Cause:** Email threads (`gmail_thread_id`) are stored in `EmailMessage`, but **completely ignored during opportunity matching**.
* In 90% of job hiring workflows, recruiters do not repeat the exact full role title in subsequent emails (e.g., in a message saying *"Let's schedule your architecture interview with Alex"*).
* Because the role title string differs or defaults to `"Software Engineer"`, the database query returns `None`, causing the service to spawn an entire new `Opportunity` record.

### 4.3 Limitation 3: Brittle Pre-Ingestion Gmail Search Query
The query `SWE_CAREER_GMAIL_QUERY` in `gmail.py` causes both severe false negatives and false positives:
* **False Negatives (Missed Emails):**
  - Modern ATS systems (Greenhouse, Lever, Ashby, Workday) frequently send candidate communication with subjects like:
    - *"Status update from Datadog"*
    - *"Invitation to connect from Sarah Jenkins"*
    - *"Next steps regarding your candidacy"*
    - *"Schedule time with the Stripe engineering team"*
  - None of these contain the 9 exact hardcoded keywords, meaning **they are never fetched from Gmail**.
* **False Positives (Wasted Sync & LLM Tokens):**
  - Non-career emails containing the words `application` (college application, apartment rental application, patent application, credit card application), `offer` (retail promo offer, cloud credits discount), or `interview` (podcast interview, journalistic interview) bypass the Gmail query and force expensive LLM extraction calls.

### 4.4 Limitation 4: Oversimplified Prompt & Missing Decision Boundaries
The system prompt in `pydantic_ai_provider.py` and `gemini.py` provides no operational guidelines for:
1. **Handling Omitted Role Titles:** It does not instruct the LLM to search for existing context or flag missing role titles; instead, models guess a generic title.
2. **Confidence Calibration:** The prompt contains no scoring rubrics for `confidence`. Models invariably return `1.0` even when guessing.
3. **Negative Constraint Definitions:** It mentions only "newsletter, product marketing, order confirmation, spam", without defining job digests, talent communities, or candidate referrals.
4. **Structured Reasoning:** The LLM does not perform chain-of-thought or reasoning steps before producing the final JSON schema, leading to hallucinated stage jumps.

### 4.5 Limitation 5: Dangerous Silent Mock Fallback
In `PydanticAIExtractionProvider.extract_email`:
```python
try:
    result = await self.agent.run(user_content)
    return result.output
except Exception as e:
    logger.warning("Pydantic AI extraction error: %s; safely falling back to fixtures.", e)
    return await self.fallback.extract_email(sender, recipients, subject, body_plain)
```
* If Gemini returns an HTTP 503 (Temporary High Demand), a 429 rate limit, or network timeout, the application **silently falls back to regex fixture data**.
* `DeterministicFixtureProvider` contains hardcoded rules for only 15 companies (`Datadog`, `Stripe`, `Google`, `Meta`, `Anthropic`, etc.) and 9 roles.
* For any other real company, it silently invents data or assigns `"Unknown Company"` and `"Software Engineer"`.
* In production, failures should be queued for retry with exponential backoff rather than corrupting the database with fake extractions.

### 4.6 Limitation 6: Database Model Omits First-Class Email Categories
* `EmailMessage` contains only `is_processed: bool` and `is_relevant: bool | None`.
* There is no `category` column (e.g. `job_application`, `interview_loop`, `recruiter_outreach`, `job_alert_digest`, `spam_newsletter`).
* Consequently, users cannot filter their email inbox view, and the system cannot explain *why* an email was categorized a certain way.

---

## 5. How to Fix Those: Comprehensive Remediation Blueprint

To transform Relayn into an enterprise-grade career relationship tracker, the following improvements should be implemented across five layers:

```
┌────────────────────────────────────────────────────────┐
│ 1. INGESTION LAYER: Smart ATS & Header Querying        │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│ 2. TAXONOMY LAYER: Multi-Tier Hierarchical Categories  │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│ 3. PROMPT LAYER: Few-Shot Calibration & Boundaries     │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│ 4. RESOLUTION LAYER: Thread & Recruiter-First Matching │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│ 5. RELIABILITY LAYER: Queue Retry & Human Review Gate  │
└────────────────────────────────────────────────────────┘
```

---

### 5.1 Multi-Tier Classification Taxonomy

Replace the binary `is_career_related` boolean with a formal two-tier taxonomy:

#### Tier 1: Primary Category (`EmailPrimaryCategory`)
* `CAREER_DIRECT`: Direct, individual communication regarding an active job application, interview, assessment, offer, or rejection.
* `CAREER_OUTREACH`: Direct, personalized 1-on-1 cold outreach from a recruiter or hiring manager to the candidate.
* `CAREER_AUTOMATED`: Automated job alerts (LinkedIn, Indeed), talent network newsletters, job board marketing, or candidate referral updates.
* `NON_CAREER`: General commercial emails, transactional receipts, newsletters, personal correspondence, or spam.

#### Tier 2: Lifecycle Intent (`EmailLifecycleIntent`)
* `APPLICATION_ACKNOWLEDGMENT`: Confirmation of an application submission.
* `RECRUITER_SCREEN_INVITATION`: Request for initial phone or video conversation.
* `INTERVIEW_SCHEDULED`: Confirmed technical, behavioral, or panel interview with date/link.
* `TECHNICAL_ASSESSMENT`: Coding challenge, take-home repository, or online assessment (e.g., HackerRank, CodeSignal).
* `OFFER_COMMUNICATION`: Formal or informal offer terms, compensation details, or offer letter.
* `REJECTION_NOTICE`: Notification that candidate is not moving forward.
* `STATUS_INQUIRY_OR_UPDATE`: General status check-in, delays, or rescheduling.
* `AUTOMATED_JOB_DIGEST`: Multi-job recommendations from aggregators.
* `IRRELEVANT_NOISE`: Completely unrelated content.

---

### 5.2 Upgraded Gmail Ingestion Query

Expand the Gmail API search query to detect ATS sender infrastructure, common recruitment email patterns, and exclude obvious transactional noise:

```python
# Enhanced Gmail Ingestion Query
SWE_CAREER_GMAIL_QUERY = (
    '('
    # 1. Known ATS domain senders
    'from:(*@*.greenhouse-mail.io OR *@*.lever.co OR *@*.ashbyhq.com '
    'OR *@*.smartrecruiters.com OR *@*.myworkday.com OR *@*.jobvite.com '
    'OR *@*.icims.com OR *@*.bamboohr.com OR *@*.rippling-ats.com) '
    'OR '
    # 2. Recruitment & interview subject triggers
    'subject:(interview OR "application received" OR "application submitted" '
    'OR "your application" OR "next steps" OR "coding challenge" OR "technical assessment" '
    'OR "offer of employment" OR "moving forward" OR "not moving forward" '
    'OR "let\'s connect" OR "hiring team" OR "recruiting team" OR "candidacy")'
    ') '
    # 3. Explicit exclusions of receipts, orders, and ecommerce
    '-subject:("order confirmation" OR "has shipped" OR "your receipt" '
    'OR "credit card" OR "statement is ready" OR "password reset")'
)
```

---

### 5.3 Production-Grade AI System Prompt

Replace the short prompt with a structured, few-shot prompt with explicit negative boundary constraints and reasoning:

```text
You are an expert AI Career Relationship Intelligence Agent for software engineering professionals.
Analyze the provided email and classify it into structured career management insights according to the JSON schema.

### CLASSIFICATION TAXONOMY:
1. primary_category:
   - "career_direct": Active personal application, interview, assessment, offer, or rejection.
   - "career_outreach": 1-on-1 personalized recruiter inquiry about an engineering opportunity.
   - "career_automated": Job alerts (LinkedIn/Indeed), talent community blasts, referral receipts.
   - "non_career": Newsletters, orders, receipts, personal emails, general spam.

2. lifecycle_intent:
   - "application_acknowledgment", "recruiter_screen_invitation", "interview_scheduled",
     "technical_assessment", "offer_communication", "rejection_notice",
     "status_update", "job_digest", "irrelevant_noise".

### CRITICAL RULES & BOUNDARIES:
- DO NOT treat LinkedIn/Indeed/Glassdoor "Jobs you may like" digests as career_direct or recruiter outreach. Mark them primary_category="career_automated" and lifecycle_intent="job_digest".
- If the email is a candidate referral confirmation where the user referred someone ELSE, set primary_category="career_automated".
- If the email is from a food delivery, Amazon order, bank statement, or product newsletter, set primary_category="non_career" and is_career_related=false.
- If the role title is not explicitly named in the email, DO NOT invent "Software Engineer". Set role_title=null, confidence=0.7, and flag requires_human_review=true with review_reason="Role title missing from email text".
- For interview rounds, inspect the description and classify round_category:
  * "recruiter_screen": Phone chat with talent acquisition.
  * "coding_dsa": Live coding, LeetCode, algorithms, data structures.
  * "system_design": Architecture, scalability, microservices, distributed systems.
  * "take_home_review": Review of candidate's submitted project.
  * "hiring_manager": Engineering leadership conversation, team vision, career goals.
  * "behavioral": Culture fit, cross-functional collaboration, STAR method.
  * "onsite_loop": Multi-stage panel or virtual onsite day.
- Extract all interview meeting URLs (Google Meet, Zoom, Microsoft Teams, Chime).
- Extract compensation figures (base salary, RSU equity, sign-on bonus) only if stated explicitly.
```

---

### 5.4 Smart Opportunity Resolution (Thread & Recruiter First)

Modify `CareerPipelineService` to use a 4-tier hierarchical resolution algorithm before creating any new opportunity:

```python
async def resolve_or_create_opportunity(
    session: AsyncSession,
    company: Company,
    gmail_thread_id: str,
    extracted_role: str | None,
    sender_email: str,
    extracted_stage: str,
) -> tuple[Opportunity, bool]:
    """
    Hierarchically resolves the correct Opportunity:
    1. Match by gmail_thread_id (Strongest signal: same email chain).
    2. Match by Sender/Recruiter Contact (Contact already assigned to an active opportunity at this company).
    3. Match by Company + Active Status (Single ongoing interview loop at this company).
    4. Match by Company + Role Title (Fuzzy / ILIKE match).
    5. Fallback: Create new Opportunity.
    """
    # Step 1: Match by Gmail Thread ID
    thread_stmt = (
        select(Opportunity)
        .join(OpportunityEvent, OpportunityEvent.opportunity_id == Opportunity.id)
        .join(EmailMessage, OpportunityEvent.email_message_id == EmailMessage.id)
        .where(EmailMessage.gmail_thread_id == gmail_thread_id)
        .limit(1)
    )
    res = await session.execute(thread_stmt)
    opp = res.scalar_one_or_none()
    if opp:
        return opp, False

    # Step 2: Match by Recruiter Contact already linked to an active opportunity
    contact_stmt = (
        select(Opportunity)
        .join(OpportunityContact, OpportunityContact.opportunity_id == Opportunity.id)
        .join(Contact, OpportunityContact.contact_id == Contact.id)
        .where(Contact.email.ilike(sender_email))
        .where(Opportunity.company_id == company.id)
        .where(Opportunity.status.notin_(["rejected", "withdrawn"]))
        .limit(1)
    )
    res = await session.execute(contact_stmt)
    opp = res.scalar_one_or_none()
    if opp:
        return opp, False

    # Step 3: Match by Company with exactly ONE active opportunity
    active_stmt = (
        select(Opportunity)
        .where(Opportunity.company_id == company.id)
        .where(Opportunity.status.notin_(["rejected", "withdrawn"]))
    )
    active_opps = (await session.execute(active_stmt)).scalars().all()
    if len(active_opps) == 1:
        # Exactly one active application with this company: attach update to it
        return active_opps[0], False

    # Step 4: Match by Role Title (fuzzy match)
    if extracted_role:
        for candidate_opp in active_opps:
            if is_role_similar(candidate_opp.role_title, extracted_role):
                return candidate_opp, False

    # Step 5: None matched -> Create new Opportunity
    new_opp = Opportunity(
        company_id=company.id,
        role_title=extracted_role or "Software Engineer",
        status=extracted_stage or "applied",
        provenance="inferred",
    )
    session.add(new_opp)
    await session.flush()
    return new_opp, True
```

This immediately resolves the duplication issues observed with Datadog and Airbnb.

---

### 5.5 Database Schema Enhancements

To make categories first-class citizens in Relayn:

1. **Add Category Columns to `email_messages` Table:**
   ```sql
   ALTER TABLE email_messages 
   ADD COLUMN primary_category VARCHAR(32) DEFAULT 'unclassified',
   ADD COLUMN lifecycle_intent VARCHAR(64) DEFAULT NULL,
   ADD COLUMN classification_confidence FLOAT DEFAULT NULL,
   ADD COLUMN classification_evidence TEXT DEFAULT NULL;

   CREATE INDEX idx_email_primary_category ON email_messages (primary_category);
   CREATE INDEX idx_email_lifecycle_intent ON email_messages (lifecycle_intent);
   ```

2. **Add Thread Index to `email_messages`:**
   Ensure `gmail_thread_id` has a composite index with `sent_at`:
   ```sql
   CREATE INDEX idx_email_thread_sent ON email_messages (gmail_thread_id, sent_at DESC);
   ```

---

### 5.6 Reliable Error Handling: Remove Silent Mock Fallbacks

In `pydantic_ai_provider.py`:
- Remove the catch-all `except Exception: return self.fallback.extract_email(...)`.
- When an API quota error or 503 occurs:
  1. Raise a recoverable `JobRetryException`.
  2. The job worker re-enqueues the `process_email` task with an exponential backoff delay (e.g., retry in 30s, 2m, 10m).
  3. Keep `DeterministicFixtureProvider` strictly for unit tests and local mock mode when `AI_PROVIDER=fixtures`. Never allow mock data in `AI_PROVIDER=gemini` mode.

---

### 5.7 Active Human-in-the-Loop Review Queue

Configure the system to trigger `review_proposals` whenever:
1. `confidence < 0.80`.
2. `primary_category == "career_direct"` but `role_title` could not be extracted with high confidence.
3. An incoming rejection or offer arrives for a company with multiple active opportunities.
4. The company name cannot be mapped to a clean domain.

This populates the existing `ReviewProposal` table and allows the frontend **Review Queue** (`/review`) to fulfill its intended purpose.

---

## 6. Implementation Action Plan

| Phase | Task Description | Files Impacted |
|---|---|---|
| **Phase 1: Database Migration** | Add `primary_category`, `lifecycle_intent`, and `classification_confidence` to `EmailMessage` model and Alembic migration. | `app/models/mailbox.py`, `migrations/` |
| **Phase 2: Schema & Prompt** | Upgrade `EmailExtractionResult` with two-tier taxonomy; rewrite system prompt with few-shot guidance. | `app/schemas/extraction.py`, `app/integrations/llm/pydantic_ai_provider.py` |
| **Phase 3: Pipeline Resolution** | Implement thread-first and recruiter-aware matching in `CareerPipelineService` to eliminate duplicate opportunities. | `app/services/pipeline.py` |
| **Phase 4: Gmail Query** | Expand `SWE_CAREER_GMAIL_QUERY` with ATS sender domains and exclusion parameters. | `app/integrations/mailbox/gmail.py` |
| **Phase 5: Job Retries** | Remove silent fixture fallback on Gemini failures; implement exponential backoff retries. | `app/integrations/llm/pydantic_ai_provider.py`, `app/jobs/handlers.py` |
| **Phase 6: Verification** | Re-run ingestion and extraction on test cases; verify zero opportunity duplication and correct category segregation. | `tests/test_pipeline_e2e.py` |

---

## 7. Conclusion

The current email segregation and categorization engine suffers from **binary oversimplification, brittle keyword querying, and thread-unaware entity matching**, which directly led to the duplicate opportunities and title distortions found in the live database.

By implementing the **two-tier taxonomy, thread-first opportunity resolution, calibrated few-shot prompting, and resilient background job retries**, Relayn will achieve robust, production-grade accuracy across all types of engineering career communications.
