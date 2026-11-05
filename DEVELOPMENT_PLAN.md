# Relayn Development Plan

This is the implementation checklist for [ARCHITECTURE.md](ARCHITECTURE.md), derived from [REQUIREMENTS.md](REQUIREMENTS.md). Only the requirements and architectural planning are complete. No application task below is implemented or tested yet.

Use the task IDs in branches, commits, or issues when useful. Completion means the listed deliverable works and its exit check passes, not merely that files exist. The plan does not create GitHub issues or authorize sending messages to others.

## 1. Delivery strategy

Build one authenticated end-to-end path using synthetic mail and the real job/service interfaces before relying on Google credentials or a paid model. Then connect the real adapters and exercise recovery. Develop related UI/API slices together rather than building every screen before the data flow works.

The initial runtime stays three services: app, worker, PostgreSQL. Treat all tasks as one application in this repository. Infrastructure expansion, user accounts, external job discovery, and autonomous email sending are not part of this plan.

For the eight-hour timebox, prioritize the demonstration path in Section 3. The full checklist also includes work needed to satisfy the broader reliability and self-hosting requirements; it is not an eight-hour delivery guarantee. Record incomplete items rather than weakening auth, deduplication, or deletion behavior.

## 2. Work breakdown

### Phase 1: Foundation, schema, and local access

| ID | Task and deliverables | Dependencies | Exit check |
| --- | --- | --- | --- |
| F01 | Scaffold `frontend/` and `backend/`, Vite/React/TypeScript, FastAPI app factory, uv/pnpm lockfiles, lint/type tooling, loopback development ports and `/api` proxy. | Planning documents | Browser loads the shell and reaches a typed API response through one development origin; unknown API paths return JSON. |
| F02 | Build Pydantic environment validation and interactive password/secret CLI; document server-only config, demo mode, and exact `.env`/Compose hash preservation. | F01 | Missing/invalid runtime secrets fail without echoing values; generated hash verifies through both supported launch paths; no secrets enter the UI build. |
| F03 | Define SQLAlchemy models, constraints/indexes, generation/version fields, OAuth request state, and Alembic migrations in logical groups. | F01, F02 | Empty PostgreSQL migrates cleanly; singleton, relationship, idempotency, temporal, and active-sync constraints reject invalid records. |
| F04 | Implement Argon2id verification, encrypted cookie sessions, CSRF/bootstrap, safe redirects, persistent per-IP/global throttling, logout and credential rotation behavior. | F02, F03 | Correct login works; direct private APIs reject missing/invalid cookies; CSRF/replay/expiry/rotation/throttle tests pass. |
| F05 | Build login, protected router shell, API client, session/cache cleanup, error display, shared query keys, and typed API contracts. | F01, F04 | Login and logout work in the browser; private caches clear on logout; the UI handles `401`, `409`, `422`, and `429` without leaking data. |

Suggested migration groups are installation/auth, mailbox/source evidence, career relationships/events, review/milestones/follow-ups, and jobs/AI diagnostics. The logical schema is complete before the corresponding feature uses it; do not let individual app/worker processes invent tables on startup.

### Phase 2: Durable execution and synthetic ingestion

| ID | Task and deliverables | Dependencies | Exit check |
| --- | --- | --- | --- |
| J01 | Implement job repository, unique keys, atomic claims, lease tokens/expiry, independent renewal/heartbeat, typed dispatch, and bounded retry/error categories. | F03 | Concurrent claims cannot own the same attempt; expired attempts recover; stale tokens cannot commit; network work never holds domain transactions open. |
| J02 | Implement worker scheduler, due polling coalescing, manual sync run IDs, pause/resume propagation, fairness/checkpoint yields, and graceful shutdown. | J01 | Repeated scheduling creates one active sync; restart produces one catch-up; manual override processes only its own children while automatic sync remains paused. |
| G01 | Define the mailbox gateway/normalizer, implement shared bounded sync handlers against the fixture gateway, and create 50-100 synthetic messages with known threads, duplicates, source availability, pagination, and failure cases. | F03, J01, J02 | Fixture ingestion uses the same gateway/handler contracts as Gmail; duplicate imports retain stable source IDs; HTML becomes safe text with no attachment/link fetches. |
| J03 | Expose authenticated job/status APIs and a minimal progress/status panel; distinguish retrieval, AI processing, blocked work, review, and stale worker. | F05, J01, J02 | The owner can see queued/running/failed counts, stop the worker, observe staleness, and retry only eligible work. |

### Phase 3: Structured AI and career records

| ID | Task and deliverables | Dependencies | Exit check |
| --- | --- | --- | --- |
| A01 | Define Pydantic extraction/change-set schemas, result fingerprints/versions, evidence validation, and the deterministic fixture provider. | G01 | Relevant, irrelevant, malformed, ambiguous, and prompt-injection fixtures produce validated outcomes without inventing missing values. |
| D01 | Implement company/contact normalization, relationship lookup, role-aware opportunity matching, and transactional proposal application with idempotent source/event keys. | A01, F03 | A recruiter conversation produces one opportunity; different openings remain separate; several contacts link to one opportunity; unrelated mail creates no career records. |
| D02 | Implement chronological status/type projection, confirmed/inferred/manual provenance, optimistic record versions, and lead-to-application conversion with submission evidence. | D01 | Old evidence does not revert newer status; repeated processing does not duplicate events; application conversion retains the same opportunity. |
| D03 | Implement review proposals and accept/edit/dismiss, manual field corrections, email reassociation, and decision history. | D02, F04 | Corrections survive reprocessing; ambiguous associations await review; repeated resolution is idempotent; stale conflicting decisions return `409`. |
| A02 | Add the real Gemini adapter, provider disclosure/acknowledgment, bounded context, limits/timeouts/retries, result reuse, and shared usage reservations. | A01, J01, F02 | Fake-provider tests cover invalid output, outage, missing key, truncation, and usage ceiling. Real mode never substitutes fixtures. An optional live smoke check is reported separately. |

Implement one structured extraction call first where feasible, keeping classification/extraction/matching responsibilities explicit in code. Do not turn each capability into an independent model call by default. The model proposes; services validate and commit.

### Phase 4: Milestones, follow-ups, and owner-facing workflow

| ID | Task and deliverables | Dependencies | Exit check |
| --- | --- | --- | --- |
| I01 | Implement milestone records, owner time-zone preference, date-only/uncertain values, source text, and rescheduling evidence. | D02 | Exact timestamps render correctly; date-only deadlines retain their date; ambiguous time zones remain explicit and reviewable. |
| I02 | Implement obligation extraction integration, deterministic follow-up refresh, due-date ticks, task identities, completion/dismissal, and terminal-state suppression. | D02, I01, J02 | Silence alone does not create indiscriminate overdue tasks; time progression works without new mail; completed/dismissed tasks stay resolved without new evidence. |
| I03 | Implement bounded read queries, filtered application/lead lists, overview metrics, and on-demand structured briefing by owner-local day. | D02, I02 | Counts agree with underlying records; refresh does not call AI repeatedly; filters and pagination are deterministic. |
| U01 | Build application/lead lists and detail page with chronology, safe email evidence, contacts, milestones, and manual edits. | F05, D03, I01, I03 | Owner can trace a record to source evidence, correct it, and distinguish applications from leads. No raw email HTML executes or loads remote images. |
| U02 | Build review and follow-up pages with pending count, evidence, conflict handling, and accept/edit/dismiss/complete actions. | F05, D03, I02 | Browser workflow resolves a proposal and task; reload/reprocessing preserves those decisions. |
| U03 | Build basic contacts and overview views plus Settings for timezone, consent, integration status, sync, jobs, and lifecycle confirmations. | J03, I03, U01, U02, A02 | A connected or demo owner can understand progress, configure non-secret preferences, and see errors without implementation traces or secrets. |

### Phase 5: Real Gmail synchronization and lifecycle control

| ID | Task and deliverables | Dependencies | Exit check |
| --- | --- | --- | --- |
| G02 | Implement Google web-client connect/callback, one-time session-bound state/PKCE, scope validation, mailbox identity, encrypted refresh credentials, and reconnect setup. | F04, F03 | Fake-Google tests reject forged, expired, replayed, or wrong-session state; a different retained mailbox cannot silently replace the current one. |
| G03 | Add the real Gmail gateway to the shared initial/incremental handlers and complete starting history boundary, all-page persistence, known-thread updates, safe cursor advancement, cursor-expiry recovery, and token refresh. | G01, G02, J02, A02 | Failure-injection tests cover arrivals during import, page restart, revoked credentials, expired history, deleted sources, duplicate polling, and AI failure after successful retrieval. |
| O01 | Implement fenced disconnect/purge controls, generation checks in all mailbox commits, restartable cleanup, token removal/revocation outcome, and explicit reimport authorization. | J01, D03, G02 | Start an extraction, purge, let the result return, and restart: no deleted record returns. Disconnect preserves records; auth/settings survive purge. |
| O02 | Implement diagnostic retention, heartbeat cleanup, structured safe logs, readiness/schema checks, and operator-facing blocked/failed recovery messages. | J03, O01 | Old diagnostics expire without deleting domain provenance; stopped worker is visible; errors/logs expose no secrets or full email content. |

G02/G03 code and fake-Google verification do not depend on the owner completing Google Console setup. Live authorization is a separate integration check requiring the owner's client configuration and a real browser session. If unavailable, document the live integration as unverified.

### Phase 6: Packaging, evaluation, and release checks

| ID | Task and deliverables | Dependencies | Exit check |
| --- | --- | --- | --- |
| O03 | Build multi-stage image, three-service Compose, migration startup procedure, development override, database-mode guard, and README run/upgrade/backup/restore instructions. | F01-F05, J01-J03, O01, O02 | A fresh authenticated demo starts with one documented workflow; built UI/API share port 3000; worker/db are not published; isolated backup restore succeeds or explicitly requests missing-key reconnection. |
| Q01 | Complete deterministic unit/PostgreSQL integration tests and evaluation reporting, including hard recovery and correction cases. | Each feature supplies tests as it is built | Requirement scenarios in Section 4 pass; fixture quality is reported separately from live-provider accuracy; no invented metrics. |
| Q02 | Add Playwright critical journey and GitHub Actions build/lint/type/migration/test/evaluation checks with synthetic data. | O03, Q01, U01-U03 | CI works without live mailbox or paid-model keys; the packaged authenticated import-to-review/follow-up journey passes. |
| Q03 | Review delivery against requirements, record incomplete/stretch items, validate setup docs, and demonstrate the final core flow. | Q02 | Another developer can run the documented demo and identify exactly which integrations were or were not verified. |

Tests are developed with each task; Phase 6 consolidates coverage and runs the complete release gates. Do not wait until the end to discover auth, migration, or job-claim defects.

### Stretch tasks, after the core gates

| ID | Feature | Prerequisites and boundary |
| --- | --- | --- |
| S01 | Career assistant and local follow-up drafting | Stable record APIs/evidence and shared AI limits. Allowlisted bounded read tools, no arbitrary SQL or external writes; hide UI until usable. |
| S02 | Additional Recharts visualizations and advanced dashboard polish | Validated metrics/read queries. Do not use charts to substitute for missing core workflows. |

No task introduces multi-user auth, hosted services, Gmail writes, attachments/OCR, Calendar permissions, external job search, or push subscriptions.

## 3. First demonstration slice

The first useful demonstration is:

1. Generate local credentials and start PostgreSQL, the app, and the worker.
2. Sign in, confirm demo mode and timezone, and enqueue synthetic import.
3. Observe retrieval/processing status while the worker creates career records.
4. Open an application and recruiter lead separately, inspect their timelines and email evidence.
5. Resolve an ambiguous match, edit a field, and complete or dismiss a follow-up.
6. Reimport/reprocess and show that records are deduplicated and corrections persist.
7. Stop/restart the worker and show recovery; perform a fenced purge and show that late work cannot restore data.

Prioritize F01-F05, J01-J03, G01, A01, D01-D03, I01-I03, minimal U01-U03, and O01/O03 enough to run that path. Use the fixture provider until A02 is ready. Keep interfaces compatible so adding real adapters is not a rewrite.

If the timebox expires before the hard recovery/packaging checks pass, describe the result as an incomplete slice with explicit failing/unverified gates, not a production-ready MVP. Google setup, full live-provider evaluation, and stretch features must not hide an unfinished core.

## 4. Requirement-to-development coverage

| Requirement area | Work items | Required validation |
| --- | --- | --- |
| Single-owner setup/auth | F02-F05 | Invalid configuration, encrypted session expiry/tampering/rotation, CSRF, persistent global/IP throttle, demo protection. |
| Gmail connection and consent | G02, A02, U03 | Read-only scope, state/session binding, provider acknowledgment, same-mailbox reconnect, no credential exposure. |
| Initial/incremental ingestion | G01, G03, J02 | All pages, known-thread replies, starting history race, expired cursor, safe retrieval checkpoint, source availability. |
| Classification and extraction | A01, A02 | Relevant/irrelevant inputs, structured validation, evidence, null fields, injection fixtures, versioned result reuse. |
| Entity/conversation resolution | D01, D03 | Native threads plus contextual checks, multiple openings, recruiter agencies, multiple contacts, ambiguous proposal review. |
| Status/history/corrections | D02, D03 | Chronological projection, manual protection, application conversion, append-only correction history, stale-version handling. |
| Follow-ups and briefing | I01-I03, U02 | Obligation-aware recommendations, time ticks, completed/dismissed suppression, timezone/date-only behavior, structured on-demand briefing. |
| Review workflow | D03, U02 | Evidence visibility, accept/edit/dismiss, repeated decision idempotency, pending count, conflict refresh. |
| Worker and operations | J01-J03, O02 | Claims/leases/heartbeat, bounded retry, fairness, pause/manual override, shutdown/restart, stale worker visibility. |
| Data deletion/privacy | O01, O02 | Generation fencing, late-result rejection, sensitive fragment removal, retained auth, explicit reimport. |
| Local distribution | O03, Q02 | Same-origin built UI, app/worker/db startup, mode-isolated databases, secrets excluded, backup/restore and upgrade docs. |
| Demo/evaluation/CI | G01, A01, Q01-Q03 | Reproducible synthetic scenarios, measured metrics, no private credentials, clean-database migrations, real versus fixture verification labeled. |
| Optional assistant/charts | S01, S02 | Bounded tools/evidence and no writes; correct measured dashboard queries. |

## 5. Failure cases that block completion

| Scenario | Expected result |
| --- | --- |
| API restarts during a sync | Durable work continues or is recovered; no dependence on an HTTP request or browser cookie. |
| Worker crashes after a provider response | Eligible attempt recovers; persisted semantic effects remain idempotent even if a provider call repeats. |
| Stale worker returns after another claim | Old lease token cannot update domain records or complete the new attempt. |
| Sync button clicked repeatedly while polling is due | One active mailbox sync; responses reuse the existing job. |
| Historical page token/history cursor becomes invalid | Safe re-enumeration/reconciliation within lookback; no lost durable data or duplicate records. |
| Model returns invalid/ambiguous output | Bounded retry or a review/failed outcome; no unvalidated career mutation. |
| Provider unavailable, key missing, or budget exhausted | Existing records remain readable; queued/blocked work has an actionable recovery path. |
| Manual correction followed by old/new conflicting mail | History is preserved; protected values do not silently revert; conflict goes to review. |
| One conversation discusses several openings | Distinct opportunities or explicit review; company/thread match alone cannot force a merge. |
| Source email is deleted | Retained history remains accessible and source is marked unavailable, without treating a transient error as deletion. |
| Purge/disconnect while an import or LLM call is active | Immediate fencing; late mutation rejected; physical purge completes through the control job. |
| Worker stopped but API healthy | Authenticated status shows stale worker and pending work rather than a false fully healthy system. |
| Real database started with demo flag | Mode guard rejects the mismatch; no fixtures inserted into real data. |
| Unknown API URL in packaged app | JSON `404`, not a successful SPA HTML response. |
| Restored database without its token key | Existing records remain readable; credential access asks for reconnection and never silently drops unreadable tokens as if nothing happened. |

## 6. Implementation handoff and completion evidence

At the start of implementation, pin supported stable runtime/library versions and provider defaults, create the module/route skeleton, and turn the first phase into code. New files should follow the architecture boundaries, with refinements recorded in ARCHITECTURE.md rather than silently diverging.

At delivery, report which task IDs are complete, what checks were actually run, which paths use fixtures, whether real Gmail/provider access was verified, and which requirements remain incomplete. Include run commands and measured evaluation output; do not report aspirational accuracy or reliability as a test result.

Use `gh` for repository/PR/Actions operations when available. No repository initialization, remote publication, GitHub issue creation, or application implementation has been performed by creating this plan.
