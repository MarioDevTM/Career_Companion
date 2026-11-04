# Career Companion

**Personal Job Search and Learning Hub**

Career Companion is a private, Python-based workspace for organizing a job search and the technical preparation that supports it. Instead of splitting applications, interview notes, CV versions, study plans, and practice questions across separate tools, it consolidates them into a single Streamlit application. An optional Ollama-powered assistant uses selected records and uploaded documents as context for targeted preparation.

* **Core workflow:** Discover opportunities → Track applications → Identify requirements → Prepare for interviews → Develop skills → Review progress
* **Deployed instance:** [careercomp.streamlit.app](https://careercomp.streamlit.app/) (private, owner-restricted workspace; not a public sign-up service)
* **Self-hosting:** Run locally with SQLite or deploy your own independent cloud instance with PostgreSQL and Google OAuth using the instructions below.

> **Project scope:** Personal productivity and learning. This is not an employer applicant tracking system (ATS), a multi-user SaaS product, or a hiring prediction service. All screenshots show fictional demonstration records and do not represent real employment history.

---

## Contents

1. [Preview](#preview)
2. [Features](#features)
3. [Technology stack](#technology-stack)
4. [Architecture](#architecture)
5. [Project structure](#project-structure)
6. [Quick start](#quick-start)
7. [Configuration](#configuration)
8. [Deploy your own instance](#deploy-your-own-instance)
9. [User guide](#user-guide)
10. [AI assistant](#ai-assistant)
11. [Persistence, exports, and backups](#persistence-exports-and-backups)
12. [Security and privacy](#security-and-privacy)
13. [Troubleshooting](#troubleshooting)
14. [Testing](#testing)
15. [Limitations and roadmap](#limitations-and-roadmap)
16. [License and references](#license-and-references)

---

## Preview

### Workspace overview

The dashboard surfaces quick actions, active applications, upcoming interviews, due follow-ups, study tasks, and spaced-revision items in one view.

![Career Companion dashboard with application and preparation summaries](https://github.com/user-attachments/assets/eb0f2474-a6f8-45e3-9c11-1b84cb613bc8)

### Module gallery

| Job applications | Interview preparation |
| --- | --- |
| ![Application tracking and status controls](https://github.com/user-attachments/assets/35987a59-a737-455f-a3c6-83b669f0e1f1) | ![Interview record and checklist](https://github.com/user-attachments/assets/661d1abb-2aa6-4bcd-9800-4b4b056b99b9) |

| Learning and revision | Context-aware AI assistant |
| --- | --- |
| ![Learning goals, quiz performance, and proficiency status](https://github.com/user-attachments/assets/0a20f6ed-1f8f-4711-87e1-3550dd69eaf4) | ![AI assistant with mode and context selection](https://github.com/user-attachments/assets/83b67c08-9463-439c-bd2b-960d65ad6d52) |

| Experience Bank | Documents |
| --- | --- |
| ![Professional experience records with evidence and competency tags](https://github.com/user-attachments/assets/d583be3d-8219-4c0c-aad0-fcc69c9c3851) | ![Document upload and version form](https://github.com/user-attachments/assets/a1c8293d-531c-4b35-aac4-2bf05065af6a) |

| Insights | Configuration and diagnostics |
| --- | --- |
| ![Application conversion and analytics dashboard](https://github.com/user-attachments/assets/662f3b47-c8ce-4dc3-b8d5-9e550a610d4b) | ![Ollama endpoint settings and live connectivity check](https://github.com/user-attachments/assets/f436d5e4-0a65-4253-8446-ff1a7713dc37) |

*Note: Screenshots were captured from the deployed dark-themed UI using illustrative demo data. Available options may vary by deployment configuration.*

---

## Features

| Module | Primary responsibilities |
| --- | --- |
| **Dashboard** | Displays active applications, upcoming interviews, due follow-ups, study tasks, spaced revisions, recent activity, and quick-navigation buttons. |
| **Applications** | Tracks companies, roles, job descriptions, sources, salary ranges, status history, contacts, deadlines, and linked documents. Supports filtering, editing, archiving, and deletion. |
| **Interviews** | Links interview stages to applications; stores schedules, participants, preparation checklists, questions for the interviewer, feedback, reflections, and follow-up actions. |
| **Learning** | Manages topics, skills, learning goals, study resources, logged sessions, notes, tasks, practice quizzes, flashcards, and spaced-revision schedules. |
| **AI Assistant** | Offers six specialized modes—Tutor, Quiz, Mock interview, Answer coach, Job analysis, and Study planner—with selectable workspace context and saved sessions. |
| **Experience Bank** | Stores verified skills, project evidence, measurable achievements, and behavioral STAR stories organized by structured fields and competency tags. |
| **Documents** | Maintains versioned CVs, cover letters, study notes, and reference files while extracting readable text for AI context. |
| **Insights** | Charts application statuses, sources, timeline trends, frequently requested skills, study hours, and quiz accuracy. |
| **Settings & Backups** | Configures display timezone, tests live Ollama connectivity, exports applications to CSV, creates full ZIP backups, and validates/restores archives with confirmation. |

### Key design principles

* **Full-lifecycle application tracking:** Roles can be saved prior to applying (`Saved`) and progressed through `Applied`, `Screening`, `Assessment`, `Interview`, `Offer`, or final outcomes. Full status history is preserved so conversion metrics accurately recognize every application that reached the interview stage, regardless of its final state. Inactivity never automatically marks an application as rejected.
* **Interview preparation with clear provenance:** AI-generated practice questions are kept strictly separate from questions confirmed as asked in real interviews. Questions can be promoted between categories as interviews happen.
* **Evidence-based learning metrics:** Self-reported confidence (`1–5`) is tracked separately from empirical performance. A skill reaches **Demonstrated Proficiency** only after completing at least **3 quiz attempts** with **80% or higher accuracy** and at least **60 minutes of logged study**. Spaced revision follows a six-stage interval ladder: **1, 3, 7, 14, 30, and 60 days**.
* **Grounded AI assistance:** The assistant can draw context from a selected job description, learning goal, uploaded document, saved note, or Experience Bank entry. System prompts instruct the model to separate explicit job requirements from inferences and never invent personal achievements. Because all responses are model outputs, verify important claims before use.

---

## Technology stack

| Layer | Technology | Role in application |
| --- | --- | --- |
| **Application & UI** | Python 3.12, Streamlit (`streamlit[auth]==1.66.1`) | Interactive UI, forms, navigation, session state, built-in OIDC authentication |
| **ORM & persistence** | SQLAlchemy 2.x | Database models, relationships, transactions, and queries |
| **Schema migrations** | Alembic | Versioned database schema migrations |
| **Local database** | SQLite | Lightweight local development storage |
| **Hosted database** | PostgreSQL (Neon) | Persistent cloud storage for application records and uploaded document bytes |
| **PostgreSQL driver** | psycopg 3 (`psycopg[binary]`) | SQLAlchemy-to-PostgreSQL connectivity |
| **Authentication** | Streamlit OIDC, Google OAuth | Verified-email sign-in and single-owner access enforcement |
| **AI inference** | Ollama HTTP API (Local or Ollama Cloud) | Streaming chat, structured JSON outputs, and live model health checks |
| **Web search (optional)** | Firecrawl HTTP API | External web retrieval for AI modes when explicitly enabled |
| **HTTP & validation** | httpx, Pydantic | Outbound requests, timeouts, response parsing, and schema validation |
| **Data & charts** | pandas, Plotly | Tabular aggregation and interactive visual analytics |
| **Document parsing** | pypdf, python-docx | Text and page/section extraction from PDF and Word documents |
| **Configuration** | python-dotenv, Streamlit Secrets | Environment variable and cloud secret management |
| **Testing** | pytest, Streamlit AppTest | Automated unit, service, and UI test suites |
| **Cloud hosting** | Streamlit Community Cloud | Application hosting and runtime execution |

*Note: This architecture does not require React, Next.js, Node.js, Docker, or external S3 object storage. Uploaded document bytes are persisted directly in PostgreSQL via `DocumentContent` records.*

---

## Architecture

```mermaid
flowchart TD
    A[Browser] -->|HTTPS| B[Streamlit application]
    B --> C{Owner access check}
    C -->|OIDC sign-in| D[Google identity provider]
    C -->|Verified owner| E[UI and Python service layer]
    E --> F[SQLAlchemy]
    F --> G[(PostgreSQL on Neon)]
    E --> H[Document parsing]
    H --> G
    E --> I[Ollama client]
    I -->|HTTPS + API key| J[Ollama Cloud or protected Ollama endpoint]
    E -.->|Optional web research| K[Firecrawl]
```

1. **Access gate before data load:** In cloud mode, the app verifies the user's Google OIDC token and confirms that `email_verified` is true and the email matches `OWNER_EMAIL` before loading any workspace data.
2. **Unified Python service layer:** Streamlit executes domain services directly in Python without a separate REST microservice.
3. **Database persistence:** Cloud deployments require PostgreSQL; local mode supports SQLite.
4. **In-database document storage:** Uploaded files and extracted text are stored in PostgreSQL (`Document` and `DocumentContent` tables), avoiding reliance on ephemeral container filesystems. Legacy local files are read from disk when present.
5. **External AI execution:** Model inference runs on Ollama Cloud or a self-hosted Ollama server rather than on the Streamlit host.
6. **Optional web retrieval:** Firecrawl is called only when a user selects a web-enabled source mode and `FIRECRAWL_API_KEY` is configured.

---

## Project structure

```text
Career_Companion/
├── app.py                        # Streamlit entry point and navigation
├── requirements.txt              # Python dependencies
├── .env.example                  # Local environment template
├── .gitignore
├── .streamlit/
│   ├── config.toml               # Streamlit theme and server settings
│   └── secrets.toml.example      # Deployment secrets template
├── alembic.ini
├── docs/
│   └── screenshots/              # UI screenshots
│       ├── applications.jpg
│       ├── assistant.jpg
│       ├── dashboard.jpg
│       ├── documents.jpg
│       ├── experience.jpg
│       ├── insights.jpg
│       ├── interviews.jpg
│       ├── learning.jpg
│       └── settings.jpg
├── migrations/
│   ├── env.py
│   └── versions/
│       ├── 0001_initial_schema.py
│       └── 0002_document_contents.py
├── src/
│   ├── access.py                 # Owner authentication and cloud-storage guard
│   ├── config.py                 # Settings resolution and configuration precedence
│   ├── database.py               # Engine, sessions, and schema initialization
│   ├── models.py                 # SQLAlchemy entities
│   ├── schemas.py                # Pydantic request/response schemas
│   ├── services/                 # Business logic and external integrations
│   │   ├── application_service.py
│   │   ├── backup_service.py
│   │   ├── demo_service.py
│   │   ├── document_service.py
│   │   ├── endpoint.py
│   │   ├── firecrawl_service.py
│   │   ├── insights_service.py
│   │   ├── learning_service.py
│   │   ├── ollama_service.py
│   │   ├── ollama_transport.py
│   │   └── request_guard.py
│   └── ui/                       # Streamlit page modules and UI helpers
├── tests/                        # pytest test suite
├── deploy/
│   └── Caddyfile.example         # Reverse-proxy template for self-hosted Ollama
├── DEPLOYMENT.md
└── VALIDATION.md
```

---

## Quick start

### Prerequisites

* **Python 3.12** (recommended) and `pip`
* **Git**
* **Optional (AI):** Local [Ollama](https://ollama.com/) installation or an Ollama Cloud API key
* **Optional (Database):** PostgreSQL instance if testing production storage locally

### 1. Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd Career_Companion
```

### 2. Create and activate a virtual environment

**Linux / macOS:**

```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Configure your local `.env`

Copy `.env.example` to `.env` and set your local preferences:

```dotenv
APP_ENV=local
AUTH_REQUIRED=false
DATABASE_URL=sqlite:///data/career_companion.db
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:0.5b
OLLAMA_API_KEY=
APP_TIMEZONE=Europe/Bucharest
```

> **Important:** Explicitly set `APP_ENV=local` for local use. When omitted, the application defaults to protected `cloud` mode. Never set `AUTH_REQUIRED=false` on an internet-facing host.

If running Ollama locally, pull your configured model and verify that the server is active:

```bash
ollama pull qwen2.5:0.5b
ollama list
ollama serve
```

### 5. Launch the application

```bash
python -m streamlit run app.py
```

Open `http://localhost:8501` in your browser. On startup, `init_db()` creates any missing tables automatically. For databases managed through Alembic, apply schema upgrades via Alembic migrations.

### Optional: Use Ollama Cloud from a local instance

To keep the app local while offloading AI inference to Ollama Cloud, update the AI variables in your untracked `.env`:

```dotenv
APP_ENV=local
AUTH_REQUIRED=false
AI_PROVIDER=ollama
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_API_KEY=YOUR_OLLAMA_CLOUD_KEY
OLLAMA_MODEL=beam:cloud
OLLAMA_NUM_CTX=16384
OLLAMA_OUTPUT_TOKENS=4096
```

*Note: Verify that the model name specified in `OLLAMA_MODEL` is available in your Ollama Cloud catalog. Models pulled locally with `ollama pull` do not automatically exist on Ollama Cloud.*

---

## Configuration

### Configuration precedence

Settings are resolved in the following order:
1. **Streamlit Secrets** (`.streamlit/secrets.toml` or Streamlit Cloud Secrets)
2. **Process environment variables**
3. **Local `.env` file**
4. **Built-in defaults**

In `cloud` mode, the Ollama endpoint and model are locked to environment-managed settings so stale database preferences cannot override deployment configuration.

| File / Location | Purpose | Commit to Git? |
| --- | --- | --- |
| `.env` | Local development configuration | **No** |
| `.env.example` | Safe placeholder template for local setup | Yes |
| `.streamlit/config.toml` | UI theme and server settings | Yes |
| `.streamlit/secrets.toml` | Local Streamlit secrets (if testing OIDC locally) | **No** |
| Streamlit Cloud **Settings → Secrets** | Production database, OAuth, and API credentials | Managed in cloud console |

### Environment variables reference

| Variable | Purpose | Default / Example |
| --- | --- | --- |
| `APP_ENV` | Runtime mode (`local` or `cloud`) | `cloud` (if omitted) |
| `AUTH_REQUIRED` | Enforces Google OIDC sign-in in local mode | `false` (local), always enforced in `cloud` |
| `OWNER_EMAIL` | Verified Google email permitted to access cloud workspace | `owner@example.com` |
| `DATABASE_URL` | SQLite or PostgreSQL connection URI | `sqlite:///data/career_companion.db` |
| `AI_PROVIDER` | AI backend identifier | `ollama` |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` or `https://ollama.com` |
| `OLLAMA_API_KEY` | Bearer token for Ollama Cloud or authenticated proxy | Empty locally; required for cloud |
| `OLLAMA_MODEL` | Target model identifier on the configured host | `qwen2.5:0.5b` or `beam:cloud` |
| `OLLAMA_NUM_CTX` | Context window budget (tokens) | `4096` |
| `OLLAMA_OUTPUT_TOKENS` | Maximum output tokens in **Detailed** response mode | `700` (capped at half of `OLLAMA_NUM_CTX`) |
| `OLLAMA_CONNECT_TIMEOUT` | Initial connection timeout (seconds) | `5` |
| `OLLAMA_FIRST_TIMEOUT` | Time-to-first-token timeout (seconds) | `120` |
| `OLLAMA_IDLE_TIMEOUT` | Stream idle timeout (seconds) | `60` |
| `OLLAMA_TOTAL_TIMEOUT` | Maximum end-to-end generation time (seconds) | `300` |
| `OLLAMA_KEEP_ALIVE` | Model keep-alive duration | `10m` |
| `FIRECRAWL_API_KEY` | API key for optional web retrieval | Empty (disables web search) |
| `FIRECRAWL_TIMEOUT` | Web search timeout (seconds) | `30` |
| `SEARCH_MAX_RESULTS` | Maximum web pages retrieved per query | `3` |
| `SEARCH_CACHE_TTL_SECONDS` | Cache lifetime for web search results (seconds) | `3600` |
| `APP_TIMEZONE` | Display timezone for schedules and timestamps | `Europe/Bucharest` |
| `MAX_UPLOAD_SIZE_MB` | Application-enforced per-file upload limit (MB) | `15` |
| `MAX_CONTEXT_CHARS` | Character ceiling for assembled AI context | `6000` |

### Streamlit Cloud Secrets template

In `src/access.py`, `st.login()` is invoked without a named provider argument, so Google OAuth settings belong directly under `[auth]`. Keep all top-level keys **above** the `[auth]` table header:

```toml
APP_ENV = "cloud"
OWNER_EMAIL = "owner@example.com"
DATABASE_URL = "postgresql://USER:PASSWORD@YOUR-NEON-POOLER-HOST/neondb?sslmode=require"

AI_PROVIDER = "ollama"
OLLAMA_BASE_URL = "https://ollama.com"
OLLAMA_API_KEY = "REPLACE_WITH_PRIVATE_OLLAMA_CLOUD_KEY"
OLLAMA_MODEL = "beam:cloud"
OLLAMA_NUM_CTX = "16384"
OLLAMA_OUTPUT_TOKENS = "4096"

FIRECRAWL_API_KEY = ""
APP_TIMEZONE = "Europe/Bucharest"
MAX_UPLOAD_SIZE_MB = "15"

[auth]
redirect_uri = "https://YOUR-APP.streamlit.app/oauth2callback"
cookie_secret = "REPLACE_WITH_RANDOM_SECRET"
client_id = "YOUR_GOOGLE_OAUTH_CLIENT_ID"
client_secret = "YOUR_GOOGLE_OAUTH_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

---

## Deploy your own instance

The live deployment at `careercomp.streamlit.app` is locked to a single owner. To deploy your own private copy on Streamlit Community Cloud:

1. **Fork or push the repository:** Confirm `app.py`, `src/`, `migrations/`, `requirements.txt`, and `.streamlit/config.toml` are committed. Never commit `.env`, `.streamlit/secrets.toml`, `data/`, or backup archives.
2. **Provision a Neon PostgreSQL database:** Create a project on Neon and copy the pooled connection string with TLS enabled (`?sslmode=require`).
3. **Configure Google OAuth:** In Google Cloud Console, create an OAuth 2.0 Web Client and register the exact callback URL: `https://YOUR-APP.streamlit.app/oauth2callback`.
4. **Create the Streamlit Cloud app:** Point Streamlit Community Cloud to your repository, branch, and `app.py` using Python 3.12.
5. **Configure Secrets:** Open **Manage app → Settings → Secrets** and paste your TOML configuration following the template above.
6. **Connect an HTTPS Ollama endpoint:** Use Ollama Cloud (`https://ollama.com`) with an API key, or place a self-hosted Ollama instance behind an authenticated TLS reverse proxy (see `deploy/Caddyfile.example`).
7. **Reboot and verify:** Sign in with your `OWNER_EMAIL` Google account, run **Settings → Run Live Ollama & Model Check**, and verify that a newly created record persists across an app reboot.

---

## User guide

### 1. Sign in and review the Dashboard

Sign in with the Google account matching `OWNER_EMAIL` (in cloud mode). The **Dashboard** summarizes active applications, upcoming interviews, due follow-ups, study tasks, and spaced revisions due today. Use the top action buttons to jump directly to common workflows.

![Career Companion dashboard overview](https://github.com/user-attachments/assets/eb0f2474-a6f8-45e3-9c11-1b84cb613bc8)

---

### 2. Track job applications

Open **Applications → Add New Application** to record the company, role title, status, priority, source, work arrangement, salary range, job description, and URL.
* Use the card tabs (**Overview & Docs**, **Edit Record**, **Status History**, **Contacts & Tasks**, **Archive / Delete**) to manage the lifecycle of each role.
* Set a concrete **Next Action** and **Due Date** (for example, *"Tailor CV for streaming pipelines before applying"*).
* Roles kept in `Saved` status are excluded from submitted-application conversion denominators.

![Job applications list and record management](https://github.com/user-attachments/assets/35987a59-a737-455f-a3c6-83b669f0e1f1)

---

### 3. Schedule and prepare for interviews

Select an application in **Interviews** and open **Log / Schedule Interview for This Application** to record the stage, date/time, participants, and preparation checklist.
* Add questions you want to ask the interviewer and record post-interview signals and personal reflections.
* Keep AI-generated practice prompts in the **Practice Bank**; only promote a question using **Mark as Confirmed Asked in Interview** if it was actually asked during a real interview.

![Interview scheduling, preparation checklist, and questions](https://github.com/user-attachments/assets/661d1abb-2aa6-4bcd-9800-4b4b056b99b9)

---

### 4. Build your Experience Bank

Open **Experience Bank → Add Entry to Experience Bank** to store verified technical skills, projects, measurable achievements, volunteering roles, and behavioral STAR stories.
* Tag entries with competencies (such as `#system-design` or `#troubleshooting`) and attach concrete supporting evidence.
* The AI Assistant uses these entries to ground interview coaching and job-fit analysis in your real background rather than inventing achievements.

![Experience Bank entries with skills and STAR stories](https://github.com/user-attachments/assets/d583be3d-8219-4c0c-aad0-fcc69c9c3851)

---

### 5. Upload CVs and reference documents

Open **Documents → Upload New Document or Version** to store `.pdf`, `.docx`, `.txt`, or `.md` files with version labels (such as `v1.0`).
* Click **Upload & Extract Text** to parse selectable text and retain page markers for AI citations.
* Scanned or image-only PDFs without selectable text are flagged transparently rather than silently treated as empty documents.
* The application enforces a **15 MB per-file limit** by default.

![Documents and version repository upload form](https://github.com/user-attachments/assets/a1c8293d-531c-4b35-aac4-2bf05065af6a)

---

### 6. Manage learning goals, quizzes, and spaced revision

Use **Learning** to track technical topics, certification prep, study resources, logged study sessions, practice quizzes, and flashcards.
* Self-confidence ratings (`1–5`) are displayed alongside empirical quiz scores and logged study minutes.
* A topic reaches **Demonstrated Proficiency** only after meeting the mastery policy (**3+ quiz attempts**, **80%+ accuracy**, and **60+ minutes of logged study**).

![Learning Hub skills, confidence ratings, and mastery status](https://github.com/user-attachments/assets/0a20f6ed-1f8f-4711-87e1-3550dd69eaf4)

---

### 7. Run context-aware sessions in the AI Assistant

Open **AI Assistant**, select one of the six modes, and attach relevant workspace context (an application, topic, learning goal, uploaded documents, saved notes, or Experience Bank records).
* Choose **My materials (no web search)** for private context analysis, or enable web retrieval when Firecrawl is configured.
* Choose **Quick** (up to 512 tokens) for concise answers or **Detailed** (up to `OLLAMA_OUTPUT_TOKENS`) for comprehensive breakdowns.

![Career and Learning Assistant mode and context configuration](https://github.com/user-attachments/assets/83b67c08-9463-439c-bd2b-960d65ad6d52)

---

### 8. Review Insights and conversion analytics

Open **Insights** to inspect submitted application counts, employer response rates, interview conversion rates, status distributions, application timelines, requested skills, and study metrics.
* Conversion percentages exclude `Saved` (unapplied) roles from denominators and inspect full status history.
* Small-sample notices appear automatically when submitted application counts are low. Metrics are descriptive historical summaries, not hiring probability predictions.

![Insights and progress analytics charts](https://github.com/user-attachments/assets/662f3b47-c8ce-4dc3-b8d5-9e550a610d4b)

---

### 9. Configure settings, diagnostics, and full backups

Open **Settings** to set your display timezone, run live Ollama connectivity and model checks, export applications to CSV, or generate a full workspace `.zip` backup.
* Use **Validate & Restore from Backup (.zip)** to preview an archive's contents before executing a transactional restore. Always export a backup of your current workspace before restoring.

![Settings, Ollama configuration, and timezone preferences](https://github.com/user-attachments/assets/f436d5e4-0a65-4253-8446-ff1a7713dc37)

---

## AI assistant

### Assistant modes

| Mode | Purpose | Key behavior |
| --- | --- | --- |
| **Tutor** | Explains technical concepts at beginner, intermediate, or deep level | Grounds explanations in selected study notes/documents with page citations when available |
| **Quiz** | Generates 1–5 multiple-choice practice questions | Validates structured JSON output and records results toward skill proficiency |
| **Mock interview** | Conducts technical, behavioral STAR, or mixed interview practice | Asks one question at a time and critiques responses |
| **Answer coach** | Reviews and refines draft interview answers | Uses Experience Bank evidence without fabricating metrics or claims |
| **Job analysis** | Compares a job description against your recorded background | Separates explicit required/preferred skills from gaps and unverified claims |
| **Study planner** | Builds a structured schedule from goals and weekly hours | Produces an actionable draft plan to review and adjust |

### Context and source modes

* **My materials (no web search):** Uses only the workspace records and documents you select.
* **Combine my materials + web:** Combines selected workspace records with live Firecrawl web results.
* **Search the web:** Queries external web sources via Firecrawl without sending selected private workspace records.

### Local Ollama vs. Ollama Cloud

| Aspect | Local Ollama | Ollama Cloud |
| --- | --- | --- |
| **Base URL** | `http://localhost:11434` | `https://ollama.com` |
| **Execution host** | Local machine or self-hosted server | Managed Ollama Cloud infrastructure |
| **Authentication** | None on loopback; Bearer token behind proxy | `OLLAMA_API_KEY` required |
| **Model availability** | Models pulled via `ollama pull` | Models available in your Ollama Cloud account |
| **Streamlit Cloud support** | Requires authenticated HTTPS tunnel/proxy | Works directly over HTTPS |

### Output token budgets and partial responses

* **Quick mode** caps generation at **512 output tokens**.
* **Detailed mode** requests up to `OLLAMA_OUTPUT_TOKENS` (constrained to at most half of `OLLAMA_NUM_CTX`).
* If generation stops early due to token limits or timeouts, the application marks the message as **incomplete**, preserves the partial text, and allows you to download it or save it as an explicitly labeled incomplete note.

---

## Persistence, exports, and backups

* **Database storage:** Local deployments can use SQLite (`data/career_companion.db`), while hosted cloud deployments require PostgreSQL (`DATABASE_URL`).
* **Document storage:** Newly uploaded files store their binary payload in PostgreSQL (`DocumentContent`) alongside extracted text and metadata (`Document`).
* **ZIP backup contents:** Full backups include supported database tables and uploaded document originals while excluding secret configuration values. Because backups contain personal career history and notes, store them securely.
* **Transactional restore:** Restoring from a `.zip` archive validates the schema and displays a non-destructive summary first. Confirming the restore replaces the current workspace data inside a database transaction.

---

## Security and privacy

* **Single-owner access control:** Cloud mode requires a verified Google OAuth account matching `OWNER_EMAIL` (case-insensitive) before any workspace queries run.
* **Credential hygiene:** Keep `DATABASE_URL`, `OLLAMA_API_KEY`, `FIRECRAWL_API_KEY`, and `[auth]` secrets strictly inside untracked `.env` files or Streamlit Cloud Secrets. If a credential is ever committed to Git history, rotate it immediately.
* **External data transmission:** Selected workspace records and uploaded document text are sent to your configured Ollama endpoint during AI requests, and web queries are sent to Firecrawl when web search is enabled. Review your providers' privacy policies before transmitting sensitive data.
* **Self-hosted Ollama security:** Never expose port `11434` directly to the public internet without TLS and authentication.

---

## Troubleshooting

| Symptom | Likely cause | Resolution |
| --- | --- | --- |
| `ModuleNotFoundError: src.access` | Source files exist locally but were not committed to Git | Check `git status`, commit missing files under `src/`, and push to the deployed branch |
| `Private workspace is locked` | Missing `OWNER_EMAIL` or `[auth]` secrets | Configure top-level `OWNER_EMAIL` and `[auth]` credentials in Streamlit Cloud Secrets |
| Google `redirect_uri_mismatch` | OAuth callback URI does not match Google Cloud Console | Register `https://YOUR-APP.streamlit.app/oauth2callback` in your Google OAuth client |
| `Cloud mode requires ... PostgreSQL DATABASE_URL` | Cloud deployment is using SQLite or missing `DATABASE_URL` | Provide a valid PostgreSQL connection string in Streamlit Cloud Secrets |
| Database connection failure | Invalid credentials, missing SSL parameter, or unreachable host | Verify the Neon pooled URI, password, `?sslmode=require`, and `psycopg[binary]` installation |
| `Cloud mode cannot use localhost` | Cloud app is pointed at `http://localhost:11434` | Point `OLLAMA_BASE_URL` to `https://ollama.com` or an authenticated HTTPS proxy |
| AI `authentication_error` | Missing, expired, or invalid `OLLAMA_API_KEY` | Verify `OLLAMA_API_KEY` in `.env` or Streamlit Secrets |
| AI `model_not_found` | Configured `OLLAMA_MODEL` is not available on the target host | Run **Live Ollama & Model Check** in Settings or verify `ollama list` / cloud catalog |
| AI `output_limit` or truncated answer | Response hit the token ceiling before completion | Switch to **Detailed** mode, increase `OLLAMA_OUTPUT_TOKENS`, or narrow the prompt scope |
| Uploaded PDF shows no extracted text | PDF contains scanned images without selectable text | Upload a text-based PDF, `.docx`, `.txt`, or `.md` file (built-in OCR is not included) |
| Local UI changes to Ollama URL/model reset | Environment variables or Streamlit Secrets lock cloud AI settings | Update `OLLAMA_BASE_URL` and `OLLAMA_MODEL` in `.env` or Streamlit Secrets and restart |

---

## Testing

The `tests/` directory covers application lifecycle logic, document parsing, learning proficiency rules, backup validation/restore, cloud access guards, Streamlit UI flows, and Ollama transport handling.

Run the automated test suite from the repository root:

```bash
python -m pytest -q
```

### Manual smoke-test checklist

1. Start the app (`python -m streamlit run app.py`) and sign in.
2. Create a job application and update its status.
3. Log an interview linked to that application and add a checklist item.
4. Log a study session and complete a practice quiz in **Learning**.
5. Upload a small `.pdf` or `.md` file in **Documents** and verify text extraction.
6. Run **Settings → Run Live Ollama & Model Check**, then generate a response in **AI Assistant**.
7. Export a full `.zip` backup in **Settings**, restart the app, and confirm all records persist.

---

## Limitations and roadmap

### Current limitations

* **Single-user design:** Built for one verified owner (`OWNER_EMAIL`); does not provide multi-tenant user isolation.
* **Provider quotas and availability:** Hosted usage depends on Neon, Google OAuth, Ollama Cloud, and optional Firecrawl limits.
* **Document constraints:** Supports `.txt`, `.md`, `.pdf`, and `.docx` up to 15 MB by default, without OCR for scanned image PDFs.

### Potential future enhancements

* Guided onboarding checklist for newly initialized workspaces
* Automated calendar/email reminders for upcoming follow-up dates
* Support for additional OpenAI-compatible AI inference providers
* Side-by-side CV version diffing against target job descriptions

---

## License and references

* **License:** No open-source license file is currently included in the project archive. All rights are reserved by the repository owner unless a license file is explicitly added.
* **Contributions:** Maintained primarily as a personal workspace project. Open an issue before proposing major changes, and never include credentials or personal data in pull requests.

### Official documentation

* [Streamlit Documentation](https://docs.streamlit.io/)
* [Streamlit Authentication (OIDC)](https://docs.streamlit.io/develop/concepts/connections/authentication)
* [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud)
* [Neon PostgreSQL Documentation](https://neon.com/docs)
* [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/)
* [Alembic Documentation](https://alembic.sqlalchemy.org/)
* [Ollama Documentation](https://docs.ollama.com/)
* [Firecrawl Documentation](https://docs.firecrawl.dev/)
* [Plotly Python Documentation](https://plotly.com/python/)
