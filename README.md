# Relayn — Autonomous AI Career Relationship Management Agent

> **Tagline:** *Your job search, on autopilot.*

Relayn is a private, local-first, autonomous career relationship management agent engineered specifically for software engineers and tech professionals. By connecting securely and directly to your Gmail inbox via read-only OAuth, Relayn continuously monitors career communications, extracts structured hiring intelligence with **Pydantic AI**, tracks multi-round technical interview loops, maintains an immutable evidence timeline, and visualizes your entire application-to-offer funnel with authentic **D3 Sankey diagrams**.

---

## 📑 Table of Contents
1. [The Problem & Why Relayn Exists](#1-the-problem--why-relayn-exists)
2. [The Core Philosophy: Autonomous Agent vs. Generic Chatbot](#2-the-core-philosophy-autonomous-agent-vs-generic-chatbot)
3. [Key Capabilities & Feature Highlights](#3-key-capabilities--feature-highlights)
4. [System Architecture & Tech Stack](#4-system-architecture--tech-stack)
5. [The Autonomous AI Agent Pipeline](#5-the-autonomous-ai-agent-pipeline)
6. [Local-First Security & Privacy Model](#6-local-first-security--privacy-model)
7. [Step-by-Step Local Setup Guide](#7-step-by-step-local-setup-guide)
8. [Google Cloud Console Setup (Live Gmail Integration)](#8-google-cloud-console-setup-live-gmail-integration)
9. [Running the Application Locally](#9-running-the-application-locally)
10. [Testing & Verification](#10-testing--verification)
11. [Troubleshooting & FAQs](#11-troubleshooting--faqs)

---

## 1. The Problem & Why Relayn Exists

In modern software engineering job searches, candidates apply to dozens or hundreds of positions across company portals (Greenhouse, Lever, Ashby, Workday), engage with recruiters over LinkedIn, schedule phone screens, submit take-home coding challenges, and go through multi-stage technical loops (DSA, System Design, Hiring Manager rounds).

### The Reality of Modern Tech Job Searches:
- **Scattered Communication**: Important emails are lost across hundreds of confirmation notices, automated rejection templates, recruiter follow-ups, and calendar invites.
- **Manual Spreadsheet Fatigue**: Job seekers frequently use Notion tables or Google Sheets, but manually updating status columns, recruiter names, and follow-up deadlines creates immense friction and quickly becomes outdated.
- **Missed Deadlines**: Take-home assessments and offer expiration deadlines slip through the cracks.
- **The "Black Hole" Problem**: It is difficult to analyze where candidates get stuck—whether resumes are rejected early (resume block) or if drop-offs happen during the technical screen or system design loops.

**Relayn solves this by eliminating manual record keeping completely.** You connect your Gmail once; the agent operates in the background, continuously maintaining your career pipeline.

---

## 2. The Core Philosophy: Autonomous Agent vs. Generic Chatbot

Relayn is **not** a chat window where you ask questions about your resume, nor is it a dumb scraper. It is an **autonomous workflow agent** governed by three principles:

1. **The User Manages Their Career; The Agent Manages the Administration.**  
   You focus on solving algorithm problems, designing distributed systems, and interviewing. The agent categorizes correspondence, logs recruiter contacts, calculates conversion rates, and flags upcoming tasks.
2. **Deterministic Governance Over Raw LLM Outputs.**  
   AI models can hallucinate. Relayn treats LLMs as **proposal engines**, not unrestrained database manipulators. Extraction results pass through strict Pydantic v2 validation and transactional state machines. Older emails cannot revert newer statuses, and low-confidence classifications are quarantined in a **Human Review Queue**.
3. **Strictly Read-Only & Zero-Exfiltration Privacy.**  
   Relayn requires only `gmail.readonly`. It **never** requests permissions to send emails, modify mailbox labels, or create drafts. Your career history remains on your local machine in your own PostgreSQL database.

---

## 3. Key Capabilities & Feature Highlights

### 📊 1. Executive Career Dashboard & 8-Stage True Sankey Diagram
- **Authentic Sankey Diagram**: Built with `d3-sankey`, featuring cubic Bézier flow ribbons whose widths are strictly proportional to applicant volume:
  $$\text{Applications} \longrightarrow \text{Screening / Ghosted / Rejected} \longrightarrow \text{OA / Take-Home} \longrightarrow \text{Tech Rounds} \longrightarrow \text{Offers}$$
- **Automatic Ghosted Detection**: Identifies applications with zero updates after 30 days and routes them to a dedicated *Ghosted / No Reply* branch.
- **Key Metrics**: Real-time *Interview Conversion Rate (%)* and *Offer Rate (%)*.

### 💻 2. Tailored Software Engineering Interview Tracking
Unlike generic trackers, Relayn understands tech hiring loops:
- **Round Categorization**: Automatically detects `recruiter_screen`, `coding_dsa`, `system_design`, `take_home_review`, `hiring_manager`, `behavioral`, and `onsite_loop`.
- **Direct Video Meeting Links**: Extracts Google Meet, Zoom, and Teams URLs directly from email invitations.
- **Interview Preparation Notes**: Surfaces candidate prep advice extracted from recruiter bodies (e.g. *"Please prepare a 10-minute presentation on a recent distributed project"*).

### 📬 3. Intelligent Dual-Mode Mailbox Gateway
- **Live Gmail Integration**: Queries your actual inbox for career keywords across a configurable lookback window (default: 12 months) with cursor-based incremental sync (`history.list`).
- **Offline Synthetic Demo Mode**: Bundled with a rich library of realistic synthetic engineering emails for immediate evaluation without Google credentials or internet access.

### 🛡️ 4. Human-in-the-Loop Review Queue
- If an email contains ambiguous data (e.g. uncertain role title or conflicting company domain), the agent flags it for human review.
- The **Review Queue** UI lets you inspect proposed changes and accept, edit, or dismiss them with one click.

### ⏰ 5. Actionable Follow-ups & Recruiter Contacts Directory
- Captures recruiter names, email addresses, and roles.
- Tracks actionable candidate commitments (e.g., *"Reply with availability for Thursday"* or *"Submit GitHub solution before Sunday 11:59 PM"*).

---

## 4. System Architecture & Tech Stack

Relayn is designed as a modular monorepo with clear separation between user interface, REST API, worker processes, and database.

```
┌────────────────────────────────────────────────────────┐
│                      Owner Browser                     │
│           (React 19 + TypeScript + Vite + Tailwind)     │
└───────────────────────────▲────────────────────────────┘
                            │ HTTP + SameSite Encrypted Cookie
┌───────────────────────────▼────────────────────────────┐
│                  FastAPI Backend Server                │
│    (/api/auth, /api/career, /api/sync, /api/settings)  │
└─────────────┬────────────────────────────┬─────────────┘
              │ Direct DB Sessions         │ Enqueue Jobs
┌─────────────▼────────────────────────────▼─────────────┐
│                   PostgreSQL Database                  │
│       - Domain Entities (Companies, Opportunities)     │
│       - Queue Table (`FOR UPDATE SKIP LOCKED`)         │
└─────────────▲────────────────────────────▲─────────────┘
              │ Lease Heartbeats           │ Claim Jobs
┌─────────────┴────────────────────────────┴─────────────┐
│               Python Background Worker                 │
│  - Periodic Mailbox Poller (5-min ticks)               │
│  - Pydantic AI Extraction Engine                       │
│  - Monotonic Status Projection & Deduplication         │
└────────────────────────────────────────────────────────┘
```

### Technology Selection:
| Layer | Technologies | Purpose |
|---|---|---|
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS, TanStack React Query, React Router, Lucide Icons | High-performance, fully typed, responsive client-side UI. |
| **Data Viz** | `d3-sankey`, `d3-shape`, `recharts` | Flow diagrams with proportional bands and interactive tooltips. |
| **Backend API** | Python 3.11+, FastAPI, Pydantic v2, Uvicorn | Asynchronous REST endpoints, typed DTOs, and automatic validation. |
| **Database** | PostgreSQL 15+, SQLAlchemy 2.0 (AsyncIO), Alembic | Transactional consistency, relational mapping, and schema migrations. |
| **Job Queue** | Native PostgreSQL Queue (`SKIP LOCKED`) | Reliable background execution without external Redis or Celery overhead. |
| **AI Framework** | Pydantic AI (`pydantic-ai`), Google Gemini (`gemini-3.8-flash`) | Type-safe agentic extraction with self-healing validation retry loops. |
| **Security** | Argon2id, AES-256-GCM, Cryptography | Master password hashing, encrypted stateless session cookies, PKCE. |

---

## 5. The Autonomous AI Agent Pipeline

```mermaid
flowchart TD
    A[Gmail Ingestion] -->|Raw Message| B[Persist in email_messages]
    B -->|Durable Job| C[PostgreSQL Job Queue]
    C -->|Claim Job| D[Background Worker]
    D -->|Sanitized Body| E[Pydantic AI Agent]
    E -->|Self-Healing Retries| F{Confidence Check}
    F -->|High Confidence| G[Career Pipeline Service]
    F -->|Ambiguous / Low Confidence| H[Review Proposals Queue]
    G --> I[Normalize Company & Contacts]
    G --> J[Monotonic Status Projection]
    G --> K[Extract SWE Interview Rounds & Tasks]
    G --> L[Commit Opportunity & Timeline Event]
```

### Extraction Workflow:
1. **Raw Persistence**: Emails are fetched from Gmail and saved to `email_messages` *before* AI extraction. An LLM outage will never lose messages or trigger re-imports.
2. **Pydantic AI Extraction**: The email's plain text is analyzed by `PydanticAIExtractionProvider` against the strict `EmailExtractionResult` schema. If an invalid field is returned, Pydantic AI sends the error back to the model for automatic correction.
3. **Resilience Fallback**: If Gemini hits a daily quota limit (`429`) or Google API spikes (`503`), the system transparently routes the email through the local **Deterministic Fixture Extractor**, ensuring 100% uptime.
4. **Monotonic Status Projection**: The pipeline enforces a unidirectional rank:
   $$\text{Lead} < \text{Applied} < \text{Screening} < \text{Assessment} < \text{Interviewing} < \text{Offer} / \text{Rejected}$$
   Historical emails arriving out of order will never demote an active offer or interview loop back to "Applied".

---

## 6. Local-First Security & Privacy Model

Relayn is built for single-tenant local ownership:
- **No Shared Cloud Accounts**: There is no public user registration, multi-tenant database, or third-party user management. Exactly one person owns the installation.
- **Local Master Password**: Protected by **Argon2id** (`RELAYN_PASSWORD_HASH`). Direct private APIs reject any request lacking a verified session.
- **AES-256-GCM Stateless Cookies**: Session data and Google OAuth refresh tokens are encrypted at rest using an AES-256-GCM key (`RELAYN_SESSION_SECRET`).
- **CSRF & Rate Limiting**: Mutating HTTP requests require matching `x-csrf-token` headers. Consecutive failed login attempts trigger progressive IP throttling (max 5 attempts per 15 minutes).
- **Generation Fencing & Safe Purge**: Clicking "Purge" increments the mailbox generation counter, immediately invalidating and cancelling any background worker jobs in flight.

---

## 7. Step-by-Step Local Setup Guide

### System Prerequisites:
- **Python**: Version `3.11` or higher.
- **uv**: Fast Python package manager (`pip install uv` or `winget install astral-sh.uv`).
- **Node.js**: Version `20+` or `24+` with **pnpm** enabled (`corepack enable pnpm`).
- **PostgreSQL**: Local PostgreSQL server running on port `5432`.

### Step 1: Clone & Navigate
```powershell
git clone <repository_url> relayn
cd relayn
```

### Step 2: Create Local Database
Open `psql` or pgAdmin and create the application database:
```sql
CREATE DATABASE relayn;
```

### Step 3: Generate Security Secrets
Navigate into `backend` and use the built-in CLI to generate your session key and master password hash:

```powershell
cd backend

# 1. Generate AES-256 session secret (32 bytes hex)
uv run python -m app.cli generate-secret

# 2. Hash your personal unlock password
uv run python -m app.cli hash-password
```
*(Copy both generated values).*

### Step 4: Configure the Environment (`.env`)
In the root directory of the project (`relayn/`), create a `.env` file (copied from `.env.example`):

```dotenv
# Application & Network
RELAYN_ENV=development
RELAYN_PORT=8000
RELAYN_HOST=127.0.0.1
RELAYN_APP_URL=http://localhost:3000

# Security (Paste your generated values here)
RELAYN_PASSWORD_HASH=$argon2id$v=19$m=65536,t=3,p=4$...
RELAYN_SESSION_SECRET=e38f5ace7d68f757ae8ff78b88ffd60f5d11bcf3e4b693bffe837a7f21512082

# Local Database (Adjust user/password if different)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/relayn

# AI Provider Configuration
AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here

# Google OAuth (Leave blank for Synthetic Demo Mode; configure for real Gmail)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

### Step 5: Run Database Migrations
Apply the initial schema and SWE interview round tables to PostgreSQL:

```powershell
cd backend
uv run alembic upgrade head
```
*(You will see Alembic apply migrations up to `cf4a4e162604` successfully).*

---

## 8. Google Cloud Console Setup (Live Gmail Integration)

To connect your real Gmail mailbox:

1. Visit the [Google Cloud Console](https://console.cloud.google.com/) and create a project named **Relayn**.
2. **Enable Gmail API**: Search for "Gmail API" and click **Enable**.
3. **Configure OAuth Consent Screen**:
   - User Type: **External** → Click **Create**.
   - App Name: `Relayn`, support email: your email.
   - **Scopes**: Click *Add or Remove Scopes*, search and select `https://www.googleapis.com/auth/gmail.readonly`.
   - **Test Users**: Click *+ Add Users* and enter your personal Gmail address.
4. **Create Web Credentials**:
   - Go to **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**.
   - Application Type: **Web application**.
   - **Authorized redirect URIs**: Add:
     ```text
     http://localhost:8000/api/auth/google/callback
     http://127.0.0.1:8000/api/auth/google/callback
     ```
5. Copy your **Client ID** and **Client Secret** into your `.env` file:
   ```dotenv
   GOOGLE_CLIENT_ID=your_id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your_client_secret
   ```

---

## 9. Running the Application Locally

Running Relayn requires three components: the Backend API, the Frontend Web UI, and the Background Worker. Open separate terminal windows:

### Terminal 1: FastAPI Backend
```powershell
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

### Terminal 2: Vite React Frontend
```powershell
cd frontend
pnpm install
pnpm dev
```

### Terminal 3: Python Background Worker
```powershell
cd backend
uv run python -m app.worker
```

Open your browser to: **`http://localhost:3000`**
1. Unlock the app using your master password.
2. In **Settings**, click **"Connect Real Gmail Account"** (or use Synthetic Demo Mode).
3. In **Dashboard** or **Opportunities**, click **"Sync Mailbox Now"**.
4. Watch the background worker process emails and populate your interactive career dashboard!

---

## 10. Testing & Verification

Relayn features comprehensive test suites covering unit logic, database queue operations, Pydantic AI extractions, Google OAuth, and end-to-end pipelines:

```powershell
cd backend

# Run the entire test suite (18 automated tests)
uv run pytest

# Run individual test modules
uv run pytest tests/test_jobs_repository.py      # Atomic queue & lease claims
uv run pytest tests/test_google_oauth.py         # PKCE & state security
uv run pytest tests/test_pydantic_ai_provider.py # AI extraction & fallback
uv run pytest tests/test_pipeline_e2e.py         # Full email-to-opportunity loop
```

---

## 11. Troubleshooting & FAQs

### Q: Why did Google say "Google hasn't verified this app"?
When using a private personal developer project in "Testing" mode, Google displays a standard warning on the consent screen. Simply click **"Advanced"** → **"Go to Relayn (unsafe)"** and proceed.

### Q: What happens if I hit the Gemini Free Tier limit?
Relayn is built with graceful degradation. If Google returns `429 Quota Exceeded`, the system logs a clean warning and transparently switches to the local deterministic extraction engine without crashing the worker or dropping any emails.

### Q: How do I switch back to Offline Synthetic Demo Mode?
Go to **Settings** (`http://localhost:3000/settings`), click **"Disconnect Mailbox"**, and click **"Purge All Career Data"**. Next time you click "Sync Mailbox Now", it will cleanly ingest the bundled 29 synthetic engineering fixtures.

---

*Relayn — Engineered for developers who want to manage their career, not their spreadsheets.*
