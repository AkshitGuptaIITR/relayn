# Build Relayn — An Autonomous AI Career Management Agent

Act as a senior AI engineer, backend architect, and full-stack developer. I want you to build a production-minded MVP of a product called **Relayn**.

Build it as a **single-user, locally runnable, self-hostable application**. We will distribute the project for people to run themselves; we will not operate a shared hosted service for them.

Do not build a generic AI chatbot or a manually maintained job application tracker. The goal is to create an intelligent personal AI agent that connects to Gmail, understands job-related conversations, automatically maintains a career pipeline, discovers opportunities, tracks recruiter relationships, and recommends what I should do next.

I have an approximately **8-hour development window**, so prioritize a working, polished, end-to-end product over excessive features or unnecessary abstractions.

---

# 1. Product Vision

## Product Name: Relayn

**Tagline: Your job search, on autopilot.**

Relayn is a personal AI-powered career relationship management system that turns a user's Gmail inbox into an intelligent, continuously updated job-search pipeline.

During a typical job search, conversations and opportunities are scattered across:

- Job application confirmation emails.
- LinkedIn notifications.
- Company career portals.
- Recruiter outreach.
- Referral introductions.
- Direct emails to founders and hiring managers.
- Interview scheduling emails.
- Technical assessment invitations.
- Rejection and offer communications.
- Follow-up conversations.

People frequently lose track of where they applied, who contacted them, which opportunities are still active, and whom they need to follow up with.

Most existing trackers depend on users manually entering and updating application details.

**Relayn should eliminate as much of that manual work as possible.**

The user connects Gmail once. Relayn reads relevant email conversations, extracts useful information, identifies opportunities, connects related conversations, maintains application statuses, and generates actionable insights.

The core principle is:

**The user manages their career. The agent manages the administrative work surrounding it.**

## Deployment and ownership model

- Each installation belongs to exactly one owner and has its own database, configuration, and Gmail connection.
- The primary experience is running the application on the owner's computer. The owner may later deploy the same application on their own server.
- Configure the owner and application secrets through a server-side `.env` file or equivalent deployment environment variables.
- Use one local password to unlock the application. Google OAuth connects Gmail after local sign-in; it does not sign the owner into Relayn.
- There is no public registration, users table, tenant model, invitation flow, role system, subscription management, or managed authentication service in the MVP.
- Different people run separate installations. Hosting an installation does not turn it into a multi-user service.
- Application records and configuration remain in storage controlled by the owner. Gmail synchronization requires Google connectivity; a configured remote LLM receives email content needed for processing. Do not describe local deployment as fully offline or guarantee that email content never leaves the machine.
- Keep the frontend and backend in this repository. The confirmed stack is **React + TypeScript + Vite**, **Python + FastAPI**, and **PostgreSQL**, with one Python background worker sharing the backend codebase.

## MVP boundaries

- Discover opportunities from imported Gmail conversations. External job-board search, LinkedIn API integration, scraping, and autonomous web browsing are outside the MVP.
- Process email metadata and text, including text extracted from HTML bodies. Attachment parsing, resume OCR, and Calendar integration are deferred.
- Generate follow-up text inside Relayn only. Do not create Gmail drafts, send messages, modify mailbox labels, or request write permissions.
- Include authenticated setup, demo mode, Gmail ingestion, background processing, opportunity history, follow-ups, and a minimal review workflow in the core vertical slice.
- Keep the daily briefing on demand. Advanced charts, relationship graphs, and the conversational assistant are stretch features after the core workflow is stable.
- Local operation requires the app, worker, and database to be running. Closing the browser or signing out does not stop authorized processing. Sleeping or shutting down the machine pauses processing; restart catches up safely.

# 2. Core Product Capabilities

Build the application around the following capabilities.

## A. Gmail Integration and Intelligent Email Ingestion

Integrate Gmail using the official Gmail API and OAuth 2.0.

Requirements:

- Require local owner authentication to connect Gmail, authorize the initial import, or change synchronization settings; see Section 4. Once authorized, the worker processes in the background without needing an active browser session.
- Use Google OAuth only to authorize access to the owner's Gmail account, independently of the local app password and session.
- Request only `https://www.googleapis.com/auth/gmail.readonly`. Do not request Gmail send/modify permissions or Calendar access. Obtain the connected mailbox address from the Gmail API profile; no Google-based app login is needed.
- Support exactly one connected Gmail mailbox per installation in the MVP.
- Retrieve relevant sent and received emails.
- Retrieve email metadata, message content, timestamps, participants, labels, and Gmail thread IDs.
- Support an initial historical synchronization.
- Support incremental synchronization without repeatedly processing previously imported emails.
- Preserve the original Gmail message and thread identifiers.
- Handle pagination, duplicate messages, rate limits, and failed synchronization gracefully.
- Provide a synchronization status indicator in the UI.

For the MVP, prioritize emails from the last 12 months. Make the lookback period configurable.

Use Gmail search queries to narrow candidate messages, including terms related to jobs, applications, recruiting, interviews, careers, hiring, referrals, opportunities, positions, and offers.

Do not assume every useful opportunity email contains these keywords. Keep the ingestion and classification logic extensible so additional discovery strategies can be added.

### Synchronization and recovery

- After the owner confirms the initial import, check for changes every **five minutes** by default. Make automatic sync and the polling interval configurable. Use outbound Gmail API polling; Cloud Pub/Sub and push subscriptions are deferred.
- Use Gmail `history.list` with the last committed `historyId` for incremental synchronization. If Gmail rejects an expired cursor with `404`, perform a fresh synchronization within the configured lookback, preserving existing records through deduplication. See [Gmail synchronization](https://developers.google.com/workspace/gmail/api/guides/sync).
- Capture a starting history boundary for the initial import and reconcile subsequent changes so messages arriving during the import are not missed. Handle all pages before declaring a sync complete.
- Persist fetched messages and their processing jobs before advancing the corresponding history checkpoint. Gmail retrieval and AI processing have separate progress: an LLM failure must not lose imported messages or require reimporting the mailbox.
- Permit at most one active synchronization for the connected mailbox. Repeated polls, retries, and repeated "Sync now" requests must not create duplicate messages, opportunities, or events.
- Include sent and received messages and updates to already-linked threads, even when a new reply lacks the original job keywords. Treat search filtering as candidate discovery, not a guarantee of complete inbox coverage.
- Persist progress and resume unfinished imports after an app or worker restart. Do not run a backlog of identical scheduled polls after downtime; enqueue one catch-up sync from the last valid cursor.
- Mark a locally stored message as unavailable when Gmail reports that it was deleted or cannot be retrieved. Keep the opportunity and historical evidence already imported until the owner explicitly deletes local data; label the source's availability accurately.
- Expose "Sync now", pause/resume, last successful sync, queued/processed/failed counts, and actionable error details. Pausing stops future polls and suspends queued mailbox processing; in-flight work stops at a safe checkpoint. An explicit one-off sync may run while automatic sync remains paused.
- Revoked authorization blocks further Gmail retrieval and requests reconnection. A disconnected mailbox must not be retried indefinitely.

Polling is the default for local installations; Gmail push requires additional Cloud Pub/Sub setup and can be considered later. See [Gmail notification guidance](https://developers.google.com/workspace/gmail/api/guides/push).

Store OAuth credentials securely. Never commit client secrets, access tokens, refresh tokens, or real email contents to Git.

The owner supplies their own Google OAuth web-client ID and secret through `.env`. Use the authorization-code flow with offline access, short-lived, single-use OAuth state bound to the initiating owner session, and a redirect URI derived from the configured application URL. Validate the state and owner session before accepting a callback; reject expired, replayed, or mismatched callbacks. Use the provider-supported PKCE flow through a maintained OAuth library.

Persist refresh tokens encrypted in the local database, with the encryption key supplied separately through `.env`. Handle consent denial, missing permissions, expired/revoked credentials, and reconnection without losing imported records. Google credentials being absent must disable Gmail connection with a useful setup message, not disable local login or demo mode.

Disconnecting Gmail removes local OAuth tokens and stops synchronization while retaining imported records unless the owner also chooses deletion. Attempt provider-side revocation and report if it could not be confirmed. Retain the disconnected mailbox identity; reconnecting the same mailbox may reuse its records. Connecting a different mailbox requires explicit confirmation and deletion of the previous mailbox's imported and derived data before replacement.

If Gmail credentials are unavailable during development, provide a functional demo mode using synthetic emails and fixtures. Demo mode must exercise the same ingestion, classification, and processing pipeline as real Gmail data. Keep demo data in a separate database from real mailbox data. Demo mode requires the same local login and must not provide an authentication bypass. If no LLM is configured, a clearly labeled deterministic fixture provider must allow the demo to run without external credentials.

## B. AI-Powered Email Classification

First determine whether a candidate email is job-related. Unrelated messages must not create career records. Every relevant email should then be analyzed and assigned one or more appropriate categories.

Support these categories:

1. APPLICATION_SUBMITTED
2. APPLICATION_CONFIRMATION
3. RECRUITER_OUTREACH
4. REFERRAL
5. DIRECT_OUTREACH
6. SCREENING
7. INTERVIEW_SCHEDULED
8. INTERVIEW_FEEDBACK
9. ASSESSMENT
10. OFFER
11. REJECTION
12. FOLLOW_UP
13. OTHER_JOB_RELATED

The classification agent should identify:

- Whether the email is incoming or outgoing.
- Whether it belongs to an existing opportunity.
- Whether it introduces a new company or opportunity.
- Whether it represents a status change.
- Whether it contains a commitment or requested action.
- Whether an actual application was submitted or the email is merely an expression of interest.
- Whether it contains a deadline or interview date.

Use an LLM with structured Pydantic outputs.

Do not rely exclusively on keyword matching. Use contextual classification, but support deterministic rules where they are more reliable.

For every classification, preserve:

- Classification category.
- Confidence score.
- Short explanation.
- Source Gmail message ID.
- Relevant evidence or extracted text.
- Processing timestamp.
- Model, prompt, and processing-pipeline versions, linked to the processing run.

Low-confidence classifications should be flagged for user review rather than silently changing important application records.

Confidence scores are decision aids, not measured accuracy guarantees. Use validation rules and configurable review thresholds alongside them. Retrying the same processing version should reuse a persisted valid result where possible; deliberate reprocessing must preserve earlier evidence and manual decisions.

## C. Opportunity and Application Extraction

The system should extract structured career opportunity information.

Each opportunity should potentially contain:

- Company name.
- Company website/domain.
- Job title.
- Job description, when available.
- Job location.
- Employment type, when available.
- Application source (LinkedIn, company website, referral, recruiter, direct outreach, etc.).
- Application date.
- Contact person's name.
- Contact email.
- Contact designation, when available.
- Referral source, when available.
- Current stage.
- Important dates.
- Last communication date.
- Next follow-up date.
- Relevant email references.

Distinguish between these opportunity types:

**APPLICATION:** A formal job application submitted by the user.

**RECRUITER_LEAD:** A recruiter or hiring representative reaches out with an opportunity.

**REFERRAL:** Someone introduces or refers the user to a company or hiring contact.

**DIRECT_OUTREACH:** The user directly contacts a company, founder, recruiter, or hiring manager about an opportunity without necessarily submitting an application.

**NETWORKING:** A career-related relationship or conversation that has not yet become a specific opportunity.

Do not create a formal application merely because a company is mentioned in an email.

An opportunity should be created using the best available information, with missing details left null instead of hallucinated.

## D. Conversation and Entity Resolution

This is one of the most important features.

A user may have multiple conversations with the same recruiter, company, or hiring manager.

Relayn must identify and connect related emails.

Implement:

1. Native Gmail thread grouping using thread IDs.
2. Company normalization using company names and email domains.
3. Contact identity resolution using sender and recipient addresses.
4. Opportunity matching using company, job title, contacts, and conversational context.
5. Deduplication of opportunities and contacts.

Example:

The user receives an email from a recruiter at Acme AI about an SDE-2 role.

The user replies, shares a resume, receives an interview invitation, and later discusses feedback.

These emails must be connected to one opportunity, not represented as four different opportunities.

However, two different job openings at the same company should remain separate opportunities where appropriate.

Do not merge opportunities just because their company names match.

Use deterministic identifiers and matching rules alongside semantic similarity. Ambiguous matches must be surfaced for review.

## E. Automated Application Status Management

Maintain a centralized status for every opportunity.

Suggested statuses:

- NEW_LEAD
- INTERESTED
- APPLIED
- RECRUITER_SCREENING
- INTERVIEWING
- ASSESSMENT
- OFFER_RECEIVED
- REJECTED
- WITHDRAWN
- NO_RESPONSE
- ON_HOLD

Implement sensible status transitions based on incoming and outgoing emails.

For example:

Application confirmation → APPLIED

Recruiter requests an introductory call → RECRUITER_SCREENING

Interview invitation → INTERVIEWING

Assessment invitation → ASSESSMENT

Offer communication → OFFER_RECEIVED

Rejection communication → REJECTED

Important:

- Do not blindly overwrite statuses when an old email is processed.
- Use chronological events and the opportunity's current state.
- Preserve an immutable application activity history.
- Store the email that caused each status transition.
- Avoid treating inferred statuses as confirmed facts.
- Expose the reason for every important status change.
- Allow users to manually correct statuses.

The system should support a distinction between confirmed, inferred, and manually edited information.

Record field provenance and manual corrections in the activity history. Reprocessing must not silently overwrite manually corrected fields or replay an old event over a newer state. New evidence that conflicts with a manual correction should produce a review item. A review decision may create an explicit corrective event rather than rewriting historical events.

## F. Follow-Up Intelligence Agent

Relayn should understand outstanding commitments and identify opportunities that need attention.

Examples:

- A recruiter has not responded for seven days.
- The user promised to share a resume but has not replied.
- A recruiter requested availability for an interview.
- An assessment deadline is approaching.
- A referral introduction has not been followed up.
- The user sent an application and has not received a response.
- An ongoing conversation has gone inactive.

Build a follow-up recommendation engine.

Each action should contain:

- Associated opportunity.
- Action description.
- Reason for the recommendation.
- Priority.
- Suggested due date.
- Source email.
- Current completion status.

Do not treat every silent conversation as overdue. Distinguish genuine follow-up opportunities from conversations where no response is expected.

Use configurable follow-up intervals and allow the user to mark actions complete or dismiss suggestions.

Reevaluate follow-ups after relevant email or owner changes and as time advances, including when no new mail arrives. Use deterministic due-date checks during the worker's periodic tick rather than making repeated LLM calls for unchanged conversations. Refreshing recommendations must not recreate completed or dismissed tasks without new supporting evidence.

## G. Daily Career Intelligence Briefing

Build a dashboard section called "Your Daily Briefing."

It should provide:

- New opportunities discovered.
- Newly identified recruiter contacts.
- Applications submitted or confirmed.
- Interviews scheduled.
- Assessments pending.
- Rejections and offers.
- Conversations requiring a response.
- Overdue follow-ups.
- Warm referral opportunities.
- Upcoming deadlines.

The briefing should be generated from structured application and activity data, not merely from an LLM summarizing the entire email inbox.

For the MVP, generate this briefing on demand when the user opens the dashboard or clicks refresh. Scheduled briefing generation is deferred; Gmail polling and email processing still run in the background.

## H. Natural-Language Career Assistant

Provide a conversational agent that can answer questions about the user's career pipeline.

Example questions:

- Which companies have I applied to in the last 30 days?
- Which recruiters haven't responded to me?
- Show all my ongoing applications.
- Which companies have I spoken to but never formally applied to?
- Do I have any warm referral opportunities?
- What are my upcoming interviews?
- Which applications have been inactive for more than two weeks?
- Which opportunities should I prioritize today?
- Show my entire conversation history with Acme AI.
- Draft a polite follow-up email to this recruiter.

The assistant must retrieve actual records from the database using controlled tools.

It must not invent companies, application statuses, contact details, dates, or conversations.

When answering, provide references to the underlying opportunity and relevant email records.

For email drafting, generate draft text inside Relayn only. Never create a Gmail draft or send emails automatically. Assistant tools must use validated, bounded queries over existing records; do not allow arbitrary SQL, shell commands, web browsing, or unrestricted database writes.

## I. Human Review and Manual Corrections

Provide a minimal review queue for low-confidence classifications, ambiguous opportunity associations, conflicting field values, and proposed status changes requiring confirmation.

Each review item must show the source email evidence, current values, proposed values, and the reason review is needed. Allow the owner to accept, edit, or dismiss the proposal and correct company/title/contact fields or email-to-opportunity associations. Save the decision and timestamp in the audit history. Prevent duplicate pending proposals, and do not resurface a dismissed proposal unless new evidence justifies it.

Apply accepted corrections through validated application services and database transactions, using the same integrity rules as automatic changes. Distinguish processing failure, a blocked integration, and a successful extraction awaiting human review in the UI.

## J. Dates, Interviews, and Deadlines

Persist interview appointments, assessment deadlines, and other important dates as structured opportunity milestones with source-email references. Store exact instants in UTC and display them in the owner's configured IANA time zone. Preserve original date text and any stated source time zone.

Represent date-only deadlines separately from exact timestamps. Do not invent a time or time zone when the email is ambiguous; keep uncertain values explicit and send consequential ambiguities for review. Time-zone changes affect display and local-day calculations, not stored event ordering.

---

# 3. User Interface and Experience

Build a polished, modern, premium-looking web application.

The application should feel like a polished personal productivity product rather than an internal admin dashboard.

Use a clean, professional design. Prefer a light theme with neutral backgrounds, thoughtful spacing, clear typography, subtle borders, and restrained accent colors.

Responsive design is desirable, but desktop is the primary target.

## Main navigation

Before the main navigation, show a simple password-only login screen. Include a password field, sign-in button, optional "Keep me signed in" checkbox, and clear error and rate-limit messages. Do not show registration, Google app sign-in, or email-based password recovery. Provide a sign-out control in the authenticated application.

Build these sections:

1. Overview
2. Applications
3. Opportunities & Leads
4. Contacts
5. Follow-ups
6. AI Assistant
7. Review
8. Settings

Show the pending review count in navigation. If the stretch-feature assistant is deferred, hide its navigation entry rather than leaving a nonfunctional screen.

## Overview dashboard

The dashboard should include:

**Top-level metrics:**

- Total applications.
- Active applications.
- Recruiter leads.
- Interviews scheduled.
- Offers received.
- Pending follow-ups.

**Visualizations:**

- Application pipeline by stage.
- Applications over time.
- Opportunity source distribution.
- Application status distribution.

**Additional sections:**

- Daily career briefing.
- Recent activity timeline.
- Priority follow-ups.
- Recently discovered opportunities.

## Applications page

Create a searchable, filterable table or board showing:

- Company.
- Position.
- Source.
- Applied date.
- Current stage.
- Recruiter/contact.
- Last activity.
- Next action.

Support filtering by company, status, application date, source, and job title.

Users must be able to open an opportunity to inspect its full details.

## Opportunity detail page

This should be one of the strongest parts of the product.

Show:

- Company and position.
- Current status.
- Contact information.
- Opportunity details.
- Application source.
- Complete chronological activity timeline.
- Related email conversations.
- Follow-up recommendations.
- AI-generated summary.
- Manual status editing.
- Field-level evidence and corrections, pending review proposals, and structured interview/deadline milestones.

Provide a way to open the original email or thread in Gmail using its native reference.

## Opportunities and leads page

Display recruiter outreach, warm leads, referrals, direct outreach, and networking conversations.

Clearly distinguish these from formal applications.

## Contacts page

Show recruiter and hiring contact profiles with:

- Name.
- Email.
- Company.
- Designation.
- Related opportunities.
- Last interaction.
- Conversation history.

## Follow-ups page

Show actionable tasks with priority, due date, reason, associated company, and completion controls.

## AI Assistant page

Provide a conversational interface for queries about the career pipeline.

Include a few example prompts that help the user discover what the agent can do.

## Review page

Show pending proposals with source evidence and accept/edit/dismiss controls. Link to the affected opportunity or email, preserve resolved decisions, and support filtering pending versus resolved items. Keep this focused on correcting career data rather than exposing internal agent implementation details.

## Settings page

Include:

- Installation owner's display name and optional contact email, read from environment configuration; these are profile information, not login credentials.
- Local session expiry and sign-out control. Explain that changing the local password requires updating `.env` and restarting the application.
- Gmail connection status.
- Connected Gmail address, granted read-only access, and connect/disconnect/reconnect controls, distinct from app login/logout.
- Google OAuth configuration status and setup instructions; never display configured secrets or tokens.
- Last synchronization time.
- Automatic sync toggle, configurable polling interval, "Sync now", pause/resume, import progress, and failed-job retry controls.
- Worker health, last heartbeat, pending/failed job counts, and sanitized integration errors.
- Configurable email lookback period.
- Configurable follow-up interval.
- Owner's IANA display time zone.
- AI provider/model status, processing limits, and acknowledgment of what email content is sent to the configured provider.
- Email-processing preferences.
- Data deletion option.
- Demo mode indicator.

Non-secret preferences such as lookback and follow-up intervals may be saved in a singleton settings record. Environment values provide defaults for these preferences. Authentication values and integration secrets remain environment-controlled and cannot be overwritten through Settings. Require explicit confirmation for data deletion; it affects this installation only and must not alter the owner's configured app password.

---

# 4. Confirmed Technical Stack and Runtime Requirements

Use a clean full-stack architecture that can be developed quickly and extended later.

Keep a modular monolith in this repository, with separate app and worker processes sharing backend modules and database models. The initial runtime has three Compose services: **app**, **worker**, and **db**. Do not introduce Redis, Celery, a vector database, or a separate scheduler service as MVP prerequisites.

## Backend

Python + FastAPI.

Responsibilities:

- Local owner authentication and session validation.
- Google OAuth integration for Gmail access only.
- Gmail synchronization.
- Email parsing.
- LLM orchestration.
- Classification and structured extraction.
- Entity resolution.
- Application state management.
- Follow-up detection.
- Assistant tool execution.
- REST API endpoints.
- Durable job submission, owner-facing progress/error APIs, and worker coordination.

Use SQLAlchemy 2.x and Pydantic.

Use Alembic for database migrations.

Use `uv` for Python dependency management and commit its lockfile. Use one backend package for HTTP routes, business services, Gmail access, AI adapters, and worker execution; the worker is not an independently maintained microservice.

## Frontend

React + TypeScript + Vite, built as a client-side application.

Use:

- Tailwind CSS.
- shadcn/ui or an equivalent reusable component system.
- Recharts for charts.
- Lucide icons.
- React Router for UI navigation.
- TanStack Query for API fetching, caching, mutations, and progress polling.

Create reusable components and consistent layouts.

Use `pnpm` for frontend dependencies and commit its lockfile. Keep frontend code in `frontend/` and Python code, migrations, and backend tests in `backend/`. Keep Compose, `.env.example`, README, and GitHub Actions configuration at the repository root or its conventional `.github/workflows/` location.

During development, configure Vite on the chosen app origin (default `http://localhost:3000`) and proxy `/api` to FastAPI. For the packaged application, build the frontend in a container build stage and let FastAPI serve the compiled assets and SPA route fallback. Never use the SPA fallback for API paths. The app and worker use the same backend image with different startup commands; Node.js is needed to build the UI, not to run a separate frontend server in the packaged installation.

Expose one browser-facing app origin. All private data comes from authenticated API requests; the static SPA shell must not contain owner data or secrets. Use lightweight progress polling initially; WebSockets are not required.

## Background worker and durable jobs

The worker owns scheduling and execution for initial imports, incremental Gmail syncs, email-processing/reprocessing jobs, and deterministic follow-up refreshes. The API validates owner actions and persists jobs, then returns promptly with a job identifier; long imports and classification must not run inside an HTTP request.

- Store jobs and resumable progress in PostgreSQL. Suggested states are `QUEUED`, `RUNNING`, `RETRY_WAIT`, `BLOCKED`, `SUCCEEDED`, `FAILED`, and `CANCELLED`. Integration setup, revoked credentials, or exhausted configured budgets should be reported as blocked work with an explicit recovery action.
- Run one worker initially, with one LLM call in flight by default. Keep scheduling in the worker, not in each API process, so API restarts or extra server workers do not duplicate schedules.
- Claim jobs atomically with a lease and maintain a heartbeat. Reclaim expired leases after a crash; a stale worker must not commit results after losing its lease. Do not hold a database transaction open during Gmail or LLM network calls.
- Assume a job can execute more than once. Use database constraints and idempotency keys for messages, processing versions, applied events, and follow-up proposals. Do not promise exactly-once execution of external LLM calls.
- Use bounded exponential backoff for transient failures, respecting provider retry guidance. Start with five automatic attempts, then retain a visible failed job for explicit retry. Missing configuration and revoked access require owner action instead of rapid retries.
- Persist checkpoint and progress counters, sanitized failure codes, attempt count, and next retry time. A failed message must not block processing unrelated messages indefinitely.
- On shutdown, stop claiming work and checkpoint or release active jobs safely. On startup, resume eligible work and schedule one catch-up poll if needed. An active owner login session is not a worker dependency.
- Track worker heartbeat separately from individual AI runs. Settings should distinguish healthy/idle, busy, stale/unavailable, and integration-blocked states based on observable timestamps and job state.
- Use FastAPI `BackgroundTasks` only for short, disposable post-response work, not as the scheduler or durable import queue.

### Pause, disconnect, and deletion coordination

Pausing suspends scheduled ingestion and queued mailbox processing; resume makes it eligible again. Logout only clears app access and does not cancel authorized work. Disconnecting stops new Gmail retrieval, cancels affected queued work, and invalidates in-flight mailbox jobs before removing tokens.

Before deleting mailbox data or replacing the connected mailbox, block new work, cancel affected jobs, and advance a persisted mailbox processing generation. Every job checks its generation and current connection state before committing changes. Discard stale results, including LLM responses arriving after a purge, so deleted data cannot reappear. Require explicit authorization to import again after a purge. Keep the app password, authentication settings, and login-throttle state independent of mailbox deletion.

## Local owner authentication

Implement single-owner password authentication in FastAPI using environment-controlled credentials, stateless encrypted sessions, and persistent login throttling.

1. **One password, no account provisioning.** The password-only login checks `RELAYN_PASSWORD_HASH`, a salted Argon2id hash generated by an included interactive CLI command. Never store the plaintext password or its hash in the database. Do not require a username or email for sign-in.
2. **Environment validation.** Refuse to start the runtime server if the password hash, session secret, token-encryption key, database URL, or application URL is missing or invalid. Reject plaintext passwords, malformed hashes, and documented placeholder secrets. Error messages identify the setting to fix without printing its value. Build/type checks may run without real runtime secrets.
3. **Stateless sessions.** FastAPI issues and validates an authenticated encrypted session cookie using a maintained library. Store only session metadata: the fixed owner identity, issue/expiry times, persistence choice, and a keyed fingerprint of the configured password hash. No session or user table is needed. Do not include email content, OAuth tokens, password hashes, or secrets in the session payload.
4. **Cookie handling.** Use `HttpOnly`, `SameSite=Lax`, `Path=/`, and a host-only cookie. Require `Secure` over HTTPS; allow a non-Secure cookie only for local loopback HTTP development. The default session expires after 24 hours; "Keep me signed in" extends it to 30 days with a matching cookie lifetime. Validate expiry server-side on every protected request. Never store auth tokens in browser localStorage.
5. **Logout and credential changes.** Logout is a protected POST that clears the cookie. Changing the password hash or session secret and restarting invalidates all existing sessions. Document that clearing a stateless cookie does not revoke a copied token before expiry; use credential rotation for global invalidation. Reset a forgotten password by generating a new hash, updating `.env`, and restarting. There is no email recovery service or in-app password editor.
6. **Protect APIs and UI routes.** FastAPI enforces session validation at the data-access boundary for all private app APIs, including synchronization, job status/control, settings, assistant tools, exports, and deletion. The SPA checks the session and redirects unauthenticated UI navigation to login; private API requests return `401`. Public responses are limited to the static app shell/assets, login/CSRF bootstrap, and a minimal health check. The Gmail callback requires the initiating owner session plus valid OAuth state; Google consent never creates a Relayn login session. The internal worker uses backend services directly under persisted owner authorization, not a browser cookie or public unauthenticated worker API.
7. **Login abuse controls.** Rate-limit failed sign-ins per client IP and across the installation. Persist counters in PostgreSQL so restarts do not clear them, with atomic updates and expiry cleanup. Start with five failures in one minute per IP and thirty in ten minutes globally, followed by increasing delays capped at fifteen minutes. Return `429` with a retry interval when blocked. Only trust forwarded client IPs from an explicitly configured reverse proxy.
8. **Request security.** Apply CSRF protection and validate request origins for login and cookie-authenticated mutations, including logout, Gmail disconnection, and data deletion. Use POST for mutations, sanitize post-login redirects to local paths, and never allow wildcard credentialed CORS. SameSite cookies alone are not the full CSRF defense.
9. **One auth authority.** Serve the frontend and `/api` under one browser origin. FastAPI serves both in the packaged installation; Vite proxies API calls in development. Publish only the app entry point and keep the worker and PostgreSQL on the private Compose network. Frontend redirects do not replace backend authorization. Keep all secrets server-side; never put them in `VITE_*` variables, frontend `.env` files, or browser bundles.
10. **Local login remains mandatory.** Both real-data and demo installations require the configured password. Do not introduce a public demo bypass, default password, or `AUTH_DISABLED` switch.

Keep the session secret separate from the stored Gmail-token encryption key so session rotation does not make mailbox credentials unreadable.

## Environment configuration and local operation

Provide a commented `.env.example` with empty secret placeholders and these settings:

| Variable | Purpose |
| --- | --- |
| `RELAYN_PASSWORD_HASH` | Required Argon2id hash for the single owner's app password. |
| `RELAYN_SESSION_SECRET` | Required cryptographically random session secret containing at least 32 bytes of entropy; also derive a separate OAuth-state key from it. |
| `RELAYN_TOKEN_ENCRYPTION_KEY` | Required independent, randomly generated 32-byte key in a documented encoding for authenticated encryption of stored OAuth tokens. |
| `RELAYN_OWNER_NAME` | Optional display name; default to "Owner". |
| `RELAYN_OWNER_EMAIL` | Optional profile contact address; does not authenticate the owner or determine the connected mailbox. |
| `RELAYN_APP_URL` | Required browser-facing origin, e.g. `http://localhost:3000`; HTTPS is required for non-loopback hosting. |
| `DATABASE_URL` | Required PostgreSQL connection string for this installation. |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Optional together; required only to connect real Gmail. |
| `GOOGLE_REDIRECT_URI` | Optional explicit override; otherwise derive `<RELAYN_APP_URL>/api/gmail/callback`. It must match the registered Google redirect URI and the configured app origin. |
| `LLM_PROVIDER` / `LLM_MODEL` / `LLM_API_KEY` | Provider configuration; requirements depend on the selected provider. Never require an API key for a fixture-only demo. |
| `LLM_MAX_CONCURRENCY` / `LLM_TIMEOUT_SECONDS` | Positive processing limits, initially one concurrent call and a 120-second timeout; permit documented overrides for the chosen provider. |
| `LLM_MAX_INPUT_CHARS` / `LLM_MAX_OUTPUT_TOKENS` | Positive request-size limits chosen within the selected model's context limits; validate and document defaults for the initial provider. |
| `LLM_DAILY_TOKEN_LIMIT` | Optional positive usage ceiling; unset means no app-enforced daily ceiling. Reaching the ceiling pauses further AI calls and exposes the reason. Provider billing remains authoritative. |
| `RELAYN_DEMO_MODE` | Defaults to `false`; when enabled, use synthetic fixtures and a separate demo database, with normal auth still required. |
| `EMAIL_LOOKBACK_MONTHS` / `FOLLOW_UP_INTERVAL_DAYS` | Initial non-secret preference defaults: 12 months and 7 days. |
| `EMAIL_AUTO_SYNC_ENABLED` / `EMAIL_POLL_INTERVAL_SECONDS` | Preference defaults: `true` and `300`. Automatic sync activates only after the owner connects Gmail and confirms the initial import. |
| `RELAYN_TIMEZONE` | Initial IANA display time zone; default to `UTC` until the owner selects their local zone during setup. |
| `RELAYN_JOB_MAX_ATTEMPTS` | Positive automatic-attempt limit; default to `5`. |
| `RELAYN_OPERATIONAL_RETENTION_DAYS` | Positive retention period for completed-job diagnostics and sanitized operational logs; default to `30`. Source evidence and review decisions follow the mailbox-data deletion policy. |

Include CLI commands to generate the password hash and random secrets without putting plaintext passwords in shell history or command-line arguments. Document a hash representation and `.env` loading/Compose escaping approach that preserves the generated value exactly, including any `$` characters; verify it through the supported launch paths.

Keep `.env`, token material, database dumps, and real-email fixtures out of Git and container images. Mount or inject configuration at runtime. Back up the token-encryption key separately from the database containing encrypted tokens. Rotating the session secret invalidates sessions without affecting stored Gmail tokens; rotating the token-encryption key requires re-encrypting stored tokens or reconnecting Gmail.

Provide Docker Compose for the app, worker, and PostgreSQL, with persistent database storage and the browser port bound to `127.0.0.1` by default. Include a documented development launch path for Vite, FastAPI, and the worker. Neither path may require a vendor-operated account, managed auth, or a hosted database. Document the owner's Google Cloud/OAuth setup, exact localhost redirect URI, applicable consent-screen/test-user limitations, and reconnection behavior. For optional server hosting, document HTTPS termination, trusted proxy configuration, secure cookies, runtime secrets, backups/restores, and a configured public app URL. Only the authenticated app entry point is browser-facing; the database and worker have no public ports. No vendor-operated hosting or automatic deployment is required.

## Database

Use PostgreSQL as the primary database.

Suggested entities/tables:

All records belong to this installation's single owner. Do not create a `users` table, dummy owner row, `user_id`/`tenant_id` columns, or per-user query filters. Contact emails and the connected Google mailbox identify career data and integrations, not app accounts.

**gmail_connections**

- id (singleton; primary key constrained to 1)
- google_email
- encrypted_credentials (nullable after disconnect)
- granted_scopes
- connection_status
- last_sync_at (last successful retrieval checkpoint, distinct from AI completion)
- sync_status
- sync_cursor (committed Gmail historyId)
- processing_generation
- initial_import_authorized_at
- next_sync_at
- last_error_code

**app_settings**

- id (singleton; primary key constrained to 1)
- email_lookback_months
- follow_up_interval_days
- auto_sync_enabled
- polling_interval_seconds
- display_timezone
- ai_processing_acknowledgment (provider destination, notice version, and acknowledgment timestamp)
- processing_preferences (JSONB)
- updated_at

**login_throttle**

- key (primary key; client IP or installation-wide bucket)
- failure_count
- window_started_at
- blocked_until
- updated_at

This table holds expiring abuse-control counters only, not owner credentials or account records.

**email_messages**

- id
- gmail_connection_id
- gmail_message_id
- gmail_thread_id
- sender
- recipients
- subject
- body_text
- sent_at
- direction
- labels
- processing_status
- source_available
- created_at

**email_classifications**

- id
- email_message_id
- agent_run_id
- category
- confidence
- extracted_data (JSONB)
- reasoning_summary
- created_at

**companies**

- id
- name
- normalized_name
- domain
- website

**contacts**

- id
- company_id
- name
- email
- designation

**opportunities**

- id
- company_id
- title
- opportunity_type
- source
- current_status
- location
- application_date
- last_activity_at
- next_follow_up_at
- confidence
- field_provenance (validated JSONB: source references, evidence type, and manual-correction metadata)
- created_at
- updated_at

**opportunity_contacts**

- opportunity_id
- contact_id
- relationship_role (recruiter, referrer, hiring manager, etc.)
- is_primary

Support multiple contacts per opportunity and multiple opportunities per contact. Enforce a unique opportunity/contact pair and at most one primary contact per opportunity.

**opportunity_emails**

- id
- opportunity_id
- email_message_id
- relationship_type

**opportunity_events**

- id
- opportunity_id
- email_message_id (nullable for an explicit owner correction)
- event_type
- previous_status
- new_status
- description
- event_date
- confidence
- evidence_type (confirmed, inferred, or manual)
- actor_type (worker or owner; not a user-table foreign key)
- idempotency_key
- recorded_at

**opportunity_milestones**

- id
- opportunity_id
- source_email_id
- milestone_type (interview, assessment_deadline, or other_deadline)
- title
- starts_at / ends_at (nullable UTC instants)
- date_only (nullable calendar date)
- source_timezone
- source_date_text
- date_precision (exact, date_only, or uncertain)
- status
- confidence

Use constraints to distinguish exact instants from date-only or unresolved values rather than fabricating timestamps.

**review_items**

- id
- opportunity_id (nullable before opportunity creation)
- source_email_id
- agent_run_id
- review_type
- current_values / proposed_changes (validated JSONB)
- reason
- proposal_key
- status (pending, accepted, edited, or dismissed)
- resolution (validated JSONB, including the owner's correction)
- created_at
- resolved_at

**follow_up_tasks**

- id
- opportunity_id
- source_email_id
- title
- description
- priority
- due_date
- status
- recommendation_key
- completed_at / dismissed_at
- created_at

**background_jobs**

- id
- job_type
- gmail_connection_id (nullable for installation-level maintenance)
- processing_generation (nullable for installation-level maintenance)
- email_message_id (nullable for whole-mailbox jobs)
- idempotency_key
- status
- priority
- payload (validated references/options only; no credentials or copied email bodies)
- progress / checkpoint (JSONB)
- attempt_count / max_attempts
- next_run_at
- lease_owner / lease_expires_at
- lease_token (changes on every claim, so a superseded attempt cannot commit)
- last_heartbeat_at
- last_error_code / last_error_summary (sanitized)
- created_at / started_at / finished_at

Sync jobs retain their pagination/checkpoint and retrieval counters here; a separate sync-runs table is not required initially. Define unique active-job keys and indexes for due jobs, expired leases, and job status. Prevent retries from reapplying already committed domain events.

**worker_heartbeats**

- worker_id (primary key)
- status
- last_seen_at
- current_job_id (nullable)

**agent_runs**

- id
- background_job_id (nullable for an interactive assistant request)
- email_message_id (nullable)
- task_type
- status
- provider / model
- prompt_version / pipeline_version
- input_fingerprint
- input_tokens / output_tokens (nullable when the provider does not report usage)
- duration_ms
- input_summary
- output_summary
- tool_trace (JSONB)
- created_at

You may refine this logical schema during architectural planning, but maintain clear relationships, database constraints, indexes, and installation-level ownership. Enforce at most one Gmail connection and one settings record. Retain the Gmail connection row and mailbox identity when disconnecting; remove its credentials. Enforce uniqueness on `(gmail_connection_id, gmail_message_id)` and appropriate junction-table, proposal, and event keys. A mailbox replacement must clear the previous mailbox's data and invalidate prior job generations before reusing the singleton connection. Use separate databases for separate installations and for demo versus real data. Private HTTP APIs require the owner's session; worker service calls require valid job ownership and processing generation instead of a browser session.

Persist source evidence and accepted/manual activity as domain data independently of disposable execution diagnostics. Expiring an old job or agent-run diagnostic must not cascade-delete classifications, review decisions, source references, or opportunity history; retain a minimal run identifier/version record or use nullable diagnostic links where necessary. Mailbox purging intentionally removes the scoped evidence and derived records, including sensitive diagnostic fragments.

Do not build unnecessary database abstractions.

## LLM and Agent Architecture

Use Gemini or another available tool-calling LLM provider.

Make the provider configurable using environment variables.

Build the initial system using clearly separated capabilities:

1. Email classification.
2. Structured information extraction.
3. Conversation and opportunity matching.
4. State transition reasoning.
5. Follow-up recommendation generation.
6. Career assistant tool execution.

Start with lightweight Python orchestration using explicit processing steps and validated provider adapters. LangGraph is optional later if graph state or branching justifies it; it is not an MVP dependency. Support the chosen real provider and deterministic fixture provider initially, keeping provider selection environment-configurable.

The LLM must not have unrestricted database write access.

Use a controlled workflow:

Email → Classification → Extraction → Entity resolution → Validation → Proposed changes → Database persistence.

Validate all LLM responses through Pydantic models.

Persist sufficient execution logs to debug failed classifications and agent decisions.

Use retries for transient provider errors and sensible timeout limits.

### AI processing policy and limits

- Before the first real import, explain which configured provider/destination receives email text and evidence snippets and require an explicit owner acknowledgment. Record the destination and notice version; a change in processing destination requires a renewed acknowledgment. Demo fixture processing does not authorize processing real emails.
- Send only the message text and relevant conversation context needed for the task. Exclude tokens, secrets, unrelated mailbox content, attachments, and remote-image contents. Make truncation visible in processing metadata; if missing context prevents a reliable decision, request review rather than inventing details.
- Enforce configurable call concurrency, input-size/output-token limits, timeouts, bounded retries, and an optional daily token ceiling. Record provider-reported usage when available, without claiming exact billing or guaranteed cost caps where usage is unavailable.
- Bound each request before making it. When the optional daily limit is reached, block new AI work and show how to resume; already in-flight calls may complete. Do not repeatedly spend tokens on unchanged classifications or regenerate unchanged briefing text automatically.
- Record model, prompt, pipeline version, source IDs, and execution status so results can be traced and deliberately reprocessed. Idempotency applies to database effects even when an external call must be repeated after interruption.
- Provider outages, invalid responses, missing API keys, and budget blocks leave imported data readable and processing recoverable. Do not silently substitute synthetic output for real mailbox processing. Surface actionable errors and allow retry after configuration or connectivity is restored.
- Keep interactive assistant requests bounded and read-only apart from owner-confirmed changes already supported by explicit app controls. They must not starve mailbox ingestion or bypass normal validation and review rules.

# 5. Agent Safety and Data Integrity

This application processes private personal email, so security and reliability are fundamental requirements.

Implement the following:

- Gmail read-only authorization.
- Local single-owner password authentication, protected APIs, CSRF protection, and rate-limited sign-in as specified in Section 4.
- Secure OAuth token handling, with Gmail consent separate from local login.
- No hardcoded secrets.
- Environment-based configuration.
- No automatic email sending.
- No automatic external writes or consequential third-party actions. Owner-authorized Gmail reads, OAuth token refresh/revocation, and calls to the acknowledged AI provider are permitted background integration operations.
- Human confirmation for uncertain or consequential changes.
- Installation-level data ownership and separate storage for demo data; no multi-user tenancy model.
- Input validation.
- Secure error handling.
- No logging of complete email bodies, passwords, password hashes, session cookies, encryption keys, or OAuth credentials.
- An option to disconnect Gmail and delete imported data.

Treat email bodies and attachments as untrusted input.

For the MVP, parse text and safe text extracted from HTML; do not download or analyze attachments. Render email text safely, strip active HTML content, and do not load tracking pixels or remote images automatically. Never fetch arbitrary links found in an email as part of classification.

Emails can contain malicious prompt injections such as instructions to reveal credentials or execute arbitrary tools. The agent must treat email content as data, not as trusted instructions.

Never let email content override system instructions or directly execute tools.

Keep every important agent decision auditable by maintaining references to original email messages.

## Data lifecycle and operational visibility

- Retain imported source text, career records, field provenance, and review decisions until the owner explicitly purges the mailbox data. Keep the imported scope limited to candidate conversations; do not retain a full unrelated inbox or add it to AI prompts.
- Purging mailbox data removes imported messages, classifications, opportunities, milestones, contact associations and imported contacts/companies, follow-ups, review evidence, processing caches, and sensitive execution fragments belonging to that mailbox. Preserve installation configuration and authentication, and coordinate with the worker as specified in Section 4.
- Activity history is append-only during normal operation; an explicit privacy purge is permitted to remove it. Prevent deleted job payloads, stale results, or caches from reconstructing purged records.
- Expire completed-job diagnostics and sanitized operational logs after the configured retention period, initially 30 days. Preserve the minimal provenance needed by domain records. Failed or blocked work remains visible until resolved, retried, or explicitly cleared.
- Provide structured operational logs with job/run IDs, stage, duration, result counts, and sanitized error codes. Do not log full prompts, complete email bodies, passwords, tokens, or session material.
- Provide a minimal public app liveness check and authenticated status for database readiness, worker heartbeat, Gmail connection, AI configuration, and backlog. A stopped worker must be visible even while the UI/API remain healthy.
- Document and verify a consistent database backup/restore procedure and separate protection of the token-encryption key. Existing owner-managed backups are not silently rewritten by a live-data purge; document their retention and the possibility that restoring an older backup restores older records.
- Before starting app/worker processes against a new schema, run migrations once and ensure both processes use a compatible schema. Document startup, graceful shutdown, recovery, and upgrade commands.

# 6. Development Priorities and Time Constraints

I have an approximately eight-hour deadline.

Do not attempt to build every future feature before getting a working end-to-end experience.

Implement in this order:

**Priority 1 — Functional foundation**

- Repository inspection.
- React/TypeScript/Vite frontend and Python/FastAPI backend setup in this repository.
- Environment configuration.
- Password/secret generation commands and validated single-owner configuration.
- Local login/logout, protected backend APIs, session expiry, and login throttling; demo mode uses the same authentication.
- PostgreSQL integration.
- Database models and migrations.
- Worker entry point, durable job storage, leases/heartbeat, and progress endpoints.
- Gmail authorization after local login, or functional authenticated demo mode.

**Priority 2 — Core AI pipeline**

- Initial Gmail import and five-minute incremental polling, with pause/resume and restart recovery.
- Email classification.
- Structured information extraction.
- Company and contact extraction.
- Thread grouping.
- Opportunity creation and deduplication.
- Provider acknowledgment, processing limits, retry/error handling, and minimal human review with preserved corrections.

**Priority 3 — Career intelligence**

- Application status tracking.
- Opportunity activity timeline.
- Follow-up detection.
- Structured interviews/deadlines and time-zone handling.
- Daily briefing generation on demand.

**Priority 4 — User experience**

- Dashboard.
- Application list.
- Opportunity details.
- Follow-ups.
- Review queue and synchronization/worker status controls.
- AI assistant if the core workflow is stable.

**Priority 5 — Quality and presentation**

- Synthetic demo dataset.
- Unit and integration tests.
- Error handling.
- README.
- Architecture diagram.
- A clear demonstration workflow.

If implementation time becomes limited, deliver a complete vertical slice instead of several incomplete features.

For the eight-hour target, deliver setup/login, an authenticated synthetic-data workflow through the durable worker, extracted opportunities and history, basic review/corrections, and follow-ups first. Include real Gmail polling when credentials are available; otherwise label the integration as unverified rather than presenting demo fixtures as live Gmail. Defer advanced charts, full assistant conversation, attachment processing, external discovery, and push subscriptions. Do not trade away authentication, data integrity, or restart recovery to display additional screens.

Prioritize Gmail ingestion, extraction, opportunity association, status tracking, and follow-up recommendations over the relationship graph or advanced conversational features.

# 7. Demo Dataset and Evaluation

Do not rely on a perfectly clean set of emails.

Create a synthetic dataset containing at least 50–100 realistic emails with diverse scenarios.

Include:

- Job application confirmations.
- Recruiter outreach.
- Direct outreach to founders.
- Referral introductions.
- Multiple emails within the same recruiter conversation.
- Multiple opportunities at the same company.
- Interview invitations.
- Assessment deadlines.
- Rejection emails.
- Offer emails.
- Unanswered follow-ups.
- Unrelated personal and promotional emails.
- Ambiguous messages.
- Duplicate messages.
- Emails with misleading or malicious instructions.
- Multiple contacts on the same opportunity, manual corrections followed by reprocessing, ambiguous time zones, and date-only deadlines.

The dataset should have known expected classifications and opportunity associations.

Build an evaluation script measuring:

- Email classification precision.
- Company and contact extraction accuracy.
- Opportunity matching accuracy.
- Application status transition accuracy.
- Follow-up detection accuracy.
- Duplicate opportunity rate.

Keep evaluation outputs reproducible.

Never invent evaluation results or claim accuracy that has not been measured.

Add deterministic integration scenarios for job retries, restarts, concurrent/duplicate sync requests, expired Gmail cursors, provider failure, and deletion while processing. Keep failure-injection tests independent of live Gmail and paid LLM calls. Report results by scenario and distinguish fixture validation from measured real-provider extraction quality.

# 8. Development Workflow and Instructions

Work in phases: finalize these requirements, produce the architectural plan and diagrams, then implement the agreed design. A request to update requirements or plan architecture does not initiate application implementation.

Before writing application code:

1. Inspect the existing repository and understand its structure.
2. Check which dependencies, files, and configurations already exist.
3. Identify the current environment and available services.
4. Prepare the architectural plan, including runtime/deployment boundaries, ingestion/processing and recovery flows, core data relationships, API/job contracts, and implementation order.
5. Begin implementation when the task moves into the implementation phase, keeping the end-to-end workflow functional.

During the implementation phase, deliver and verify working software rather than stopping at an architecture-only deliverable. During requirements and architecture work, complete the requested phase first.

Make sensible engineering decisions autonomously. Do not repeatedly ask me to choose between minor implementation alternatives.

Use clean code, sensible separation of concerns, type annotations, error handling, and meaningful comments.

Avoid unnecessary microservices. This should initially be a modular monolith with clean internal boundaries.

Create:

- Backend application.
- Frontend application.
- Worker command using shared backend services, durable jobs, and observable scheduling.
- Database migrations.
- `.env.example` with single-owner authentication and Gmail integration configuration documented separately.
- Interactive password-hash and secret-generation commands.
- Docker Compose configuration for app, worker, and PostgreSQL, with persistent data and localhost-only browser access by default.
- Synthetic email fixtures.
- Evaluation scripts.
- README with setup and run instructions.

Use pytest for backend and worker integration tests, Vitest for meaningful frontend logic tests, and Playwright for the critical browser journey. GitHub Actions should run relevant lint/type/build, tests, and migration checks with synthetic data and local test services. Do not require private mailbox credentials, paid provider keys, or deployment access for pull-request checks.

Use the GitHub CLI (`gh`) for GitHub repository inspection, issues, pull requests, and GitHub Actions operations such as viewing workflow runs and logs. Do not substitute a browser workflow when `gh` can perform the requested operation. If CLI network access is blocked, report the limitation and use an available read-only connector for reference inspection; do not claim a `gh` operation succeeded. Do not add deployment workflows merely to support local operation.

Keep frontend and backend integration functional throughout development.

After implementation:

1. Run backend tests.
2. Run frontend build/type checks.
3. Verify database migrations.
4. Test the complete authenticated demo workflow, including the worker, review decisions, and recovery cases.
5. Fix obvious bugs.
6. Document any unfinished integrations honestly.

## Authentication and self-hosting acceptance checks

- A fresh installation can generate its password hash and secrets, configure `.env`, start locally, and sign in without a Google account or hosted auth service. Invalid or missing required auth configuration prevents runtime startup without revealing values.
- Correct passwords create sessions; incorrect passwords do not. Unauthenticated UI navigation redirects to login, and direct private API requests return `401`, including in demo mode. A publicly served static SPA shell contains no private data.
- Expired, tampered, and old-password/old-session-secret cookies are rejected. Both session lifetimes, cookie flags, sign-out, CSRF rejection, and safe login redirects are verified.
- Repeated failed sign-ins produce a bounded retry delay that survives an app restart; untrusted forwarded headers do not bypass the installation-wide limit.
- Google consent connects the one mailbox only after local login; denied consent, invalid/replayed state, and revoked tokens are handled. Signing out of Relayn does not revoke Gmail; disconnecting Gmail does not sign the owner out.
- Missing Google credentials still allow authenticated demo use. Demo data cannot mix with a real mailbox, and changing to another mailbox cannot silently retain the previous mailbox's records.
- The schema contains no users table or owner/tenant foreign keys. Stored OAuth credentials are encrypted, and no secret is exposed through frontend bundles, API responses, logs, Git, or container images.
- Restarting preserves imported data. Document and verify backup/restore, including the token-encryption key, and an HTTPS deployment configuration exposing only the app origin, with no public database or worker port.

## Background processing and data-integrity acceptance checks

- A local Compose launch starts the app, worker, and PostgreSQL. The built Vite frontend and API work under one origin, and private API data remains unavailable without authentication.
- Closing the browser or signing out does not stop previously authorized polling. Pausing prevents scheduled retrieval and queued processing; disconnecting stops retrieval and invalidates affected work. "Sync now" is a deliberate one-off action and does not silently change the automatic-sync preference.
- Interrupt a historical import or processing job, restart the worker, and verify safe recovery from persisted progress. Expired leases are reclaimable, and stale workers cannot commit results.
- Import the same fixture set twice and trigger simultaneous manual/scheduled syncs: message, opportunity-event, milestone, and follow-up counts do not grow through duplicate processing. Reprocessing preserves manual corrections and completed/dismissed actions.
- Simulate Gmail history-cursor expiry, pagination, new messages during initial import, deleted sources, and token revocation. Verify catch-up or an actionable blocked state with no silent data loss.
- Simulate transient provider failure, invalid structured output, missing credentials, and a configured usage ceiling. Existing career data stays readable, retries are bounded, and eligible jobs resume after the owner resolves the cause.
- Create ambiguous matches and conflicting statuses. Verify review evidence and accept/edit/dismiss behavior, persistence of decisions, and no automatic overwrite of protected corrections.
- Verify UTC ordering, owner-local day calculations, exact interview times, date-only deadlines, and unresolved temporal ambiguity without invented timestamps.
- Purge data while a job is running or awaiting an LLM response. After the stale work returns and the worker restarts, purged records remain absent and reimport requires explicit authorization.
- Stop the worker while keeping the app running: authenticated Settings exposes a stale heartbeat and pending work. Logs and error responses contain useful identifiers without secrets or full email content.
- Restore a documented backup into an isolated test installation, verify migrations and source relationships, and either decrypt credentials with the separately restored key or show an explicit reconnection requirement.

# 9. Expected Final Product

At the end, I should be able to:

1. Configure my installation, open Relayn, and sign in with my local owner password.
2. Connect my Gmail account through separate Google consent, or enter authenticated demo mode.
3. Import historical job-related emails.
4. Watch the AI processing pipeline discover opportunities.
5. See formal applications and recruiter leads separately.
6. Open an opportunity and inspect all associated conversations.
7. See automatically reconstructed application histories.
8. See current statuses and outstanding follow-ups.
9. Get a daily career briefing.
10. Ask natural-language questions about my job search, provided the assistant functionality is implemented.
11. Review uncertain findings, correct career records, and retain those corrections during later processing.
12. Control automatic polling, inspect processing progress, and recover from interruptions without duplicate or resurrected records.

The final interface should look polished enough to demonstrate to an AI engineering recruiter.

The project should be easy to run locally and easy to extend beyond the initial MVP. Another person can run their own independent installation, and I can move mine to a server without adding user accounts or changing the authentication model.

# 10. Product Philosophy

Keep these principles in mind throughout development:

- This is an AI agent, not merely an email parser.
- The system should maintain career context over time.
- Every important conclusion must have supporting email evidence.
- The agent should distinguish actual applications from leads and conversations.
- Avoid duplicate opportunities and incorrect status changes.
- Use deterministic logic for things that do not require an LLM.
- Use LLMs for contextual understanding, ambiguity resolution, and reasoning.
- The user should remain in control of important actions.
- The interface should focus on actionable career intelligence rather than just displaying email data.

**The ultimate goal: I should never have to manually maintain a spreadsheet of my job applications again. Relayn should continuously understand where I stand in my job search and tell me what deserves my attention next.**

Use this document as the input to the next architectural-planning phase. Define the deployment view, email-processing/recovery sequence, core data model, and implementation milestones before starting application code.
