# Career Companion

### Personal Job Search & Learning Hub

Career Companion is a private, Python-based workspace for organizing a job search and the learning that supports it. Instead of keeping applications, interview notes, CV versions, study plans, and practice questions in separate tools, it brings them together in one Streamlit application. An optional Ollama-powered assistant uses selected records and documents as context for focused preparation.

**Workflow:** Discover opportunities -> Track applications -> Identify requirements -> Prepare for interviews -> Develop skills -> Review progress.

**Deployed instance:** [careercomp.streamlit.app](https://careercomp.streamlit.app/) — a **private, owner-restricted workspace**, not a public sign-up service. To use Career Companion yourself, run it locally or deploy your own independent instance using the instructions below.

> **Project scope:** Personal productivity and learning. This is not an applicant tracking system for employers, a multi-user SaaS product, or a hiring prediction service. Screenshots contain fictional demonstration records and should not be interpreted as real employment history.

## Contents

- [Preview](#preview)
- [Features](#features)
- [Technology stack](#technology-stack)
- [Architecture](#architecture)
- [Project structure](#project-structure)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Deploy your own instance](#deploy-your-own-instance)
- [User guide](#user-guide)
- [AI assistant](#ai-assistant)
- [Persistence, exports, and backups](#persistence-exports-and-backups)
- [Security and privacy](#security-and-privacy)
- [Troubleshooting](#troubleshooting)
- [Testing](#testing)
- [Limitations and roadmap](#limitations-and-roadmap)
- [License and references](#license-and-references)

## Preview

**Workspace overview** — quick actions, active applications, interviews, follow-ups, study tasks, and recent activity.

![Career Companion dashboard with application and preparation summaries](docs/screenshots/dashboard.jpg)

<details>
<summary>Explore more screenshots</summary>

| Job applications | Interview preparation |
| --- | --- |
| ![Application tracking and status controls](applications.jpg) | ![Interview record and checklist](docs/screenshots/interviews.jpg) |

| Learning and revision | Context-aware AI assistant |
| --- | --- |
| ![Learning goals, quiz performance, and proficiency status](docs/screenshots/learning.jpg) | ![AI assistant with mode and context selection](docs/screenshots/assistant.jpg) |

| Experience Bank | Documents |
| --- | --- |
| ![Professional experience records with evidence and competency tags](docs/screenshots/experience.jpg) | ![Document upload and version form](docs/screenshots/documents.jpg) |

| Insights | Configuration and diagnostics |
| --- | --- |
| ![Application conversion and analytics dashboard](docs/screenshots/insights.jpg) | ![Ollama endpoint settings and live connectivity check](docs/screenshots/settings.jpg) |

</details>

Screenshots were captured from the deployed dark-themed UI. Their data is illustrative; configuration and available options can differ between deployments.

## Features

| Module | What it does |
| --- | --- |
| **Dashboard** | Highlights active applications, upcoming interviews, due follow-ups, study tasks, spaced revisions, and recent activity. Provides quick navigation to common actions. |
| **Applications** | Records companies, roles, descriptions, sources, salary details, status history, contacts, deadlines, and linked documents; supports filtering, editing, archiving, and deletion. |
| **Interviews** | Links interviews to applications; stores schedules, participants, preparation checklists, interviewer questions, feedback, reflections, and follow-up actions. |
| **Learning** | Maintains topics, skills, learning goals, study resources, sessions, notes, tasks, quizzes, flashcards, and a revision schedule. |
| **AI Assistant** | Provides six modes—Tutor, Quiz, Mock interview, Answer coach, Job analysis, and Study planner—with selectable context and saved sessions. |
| **Experience Bank** | Stores skills, project evidence, achievements, and STAR stories using structured fields and competency tags. |
| **Documents** | Stores versioned CVs, cover letters, study notes, and reference files; extracts readable text for the assistant. |
| **Insights** | Visualizes application status, sources, trends, requested skills, study activity, and quiz performance. |
| **Settings & Backups** | Configures the timezone, checks the Ollama connection, exports applications, prepares ZIP backups, and validates/restores backups with confirmation. |

### Application tracking

Applications can be recorded before submission using **Saved**, then advanced through statuses such as **Applied**, **Screening**, **Assessment**, **Interview**, **Offer**, or other applicable outcomes. Status history is retained, allowing analytics to recognize that an application reached an interview even if its current status later changed. The record can include priority, working arrangement, employment type, salary range, a job URL, and next action with due date.

### Interview preparation with provenance

The interview workspace keeps **AI-generated practice** questions separate from questions **confirmed as asked in an actual interview**. Users can promote or move questions between those categories as the facts change. Preparation checklists, interviewer questions, answer notes, feedback, and personal reflections remain attached to the selected interview.

### Learning without inflated proficiency scores

Learning tracks **self-confidence (1–5)** separately from measured practice. In the inspected implementation, a skill reaches **Demonstrated Proficiency** only after **at least three quiz attempts**, **80% or higher accuracy**, and **at least 60 logged study minutes** for that skill. Insufficient evidence is not presented as mastery. Spaced revision uses a six-stage interval ladder of **1, 3, 7, 14, 30, and 60 days**.

### Evidence-grounded career assistance

The assistant can incorporate a selected job description, skill or learning goal, uploaded documents, saved notes, and Experience Bank entries. Its instructions emphasize separating explicit job requirements from inferences and avoiding invented personal achievements. Generated advice is still model output and should be checked before use.

## Technology stack

The table below reflects the supplied project archive and the deployed screenshots, not a hypothetical framework stack.

| Layer | Technology | Responsibility |
| --- | --- | --- |
| Application & UI | **Python**, **Streamlit** (`streamlit[auth]==1.66.1` in the inspected archive) | Interactive UI, forms, navigation, session handling, built-in OIDC support |
| ORM & persistence | **SQLAlchemy 2.x** | Database models, relationships, queries, and sessions |
| Database migration | **Alembic** | Versioned database schema migrations |
| Local database | **SQLite** | Optional local development storage |
| Hosted database | **PostgreSQL**, hosted on **Neon** | Persistent production records and document bytes |
| PostgreSQL driver | **psycopg 3** (`psycopg[binary]`) | SQLAlchemy/PostgreSQL connectivity |
| Authentication | **Streamlit OIDC**, **Google OAuth** | Sign-in and verified-email owner restriction |
| AI | **Ollama HTTP API**; local Ollama or **Ollama Cloud** | Streaming chat, structured assistance, model checks |
| External search (optional) | **Firecrawl** via HTTP | Web retrieval for AI modes that request it |
| HTTP & validation | **httpx**, **Pydantic** | Service requests, response parsing, structured validation |
| Analysis | **pandas** | Aggregation and tabular metrics |
| Charts | **Plotly** | Interactive charts and analytics |
| Document parsing | **pypdf**, **python-docx** | Extract text and page/section information |
| Configuration | **python-dotenv**, Streamlit Secrets | Local and hosted settings |
| Testing | **pytest**, Streamlit AppTest | Unit, integration-oriented, and UI tests in the repository |
| Hosting | **Streamlit Community Cloud** | Runs the Python application |

**Not required by the inspected application:** React, Next.js, a Node.js application backend, Neon Functions, Neon Auth, S3 object storage, or Docker. An S3 service may exist in the owner's Neon project, but the inspected Career Companion document implementation stores newly uploaded file bytes in the database.

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

1. **Authentication happens before workspace data is loaded.** The cloud application requires a verified Google email matching `OWNER_EMAIL`.
2. **Streamlit executes the application services** in Python. This is not a separately deployed REST backend.
3. **SQLAlchemy provides persistence.** Streamlit Cloud uses PostgreSQL; local mode can use SQLite.
4. **New document originals and extracted metadata** are saved in PostgreSQL through `Document` and `DocumentContent` records. Legacy file-based attachments are read from local storage when present.
5. **Ollama runs inference outside Streamlit.** The deployed app connects to a cloud service or a separately secured HTTPS Ollama host; it does not install AI models on the Streamlit server.
6. **Firecrawl is optional.** Search-enabled requests use it only when configured; private-materials-only modes do not require it.

## Project structure

The following is based on the supplied project archive; your live Git branch may contain later changes.

```text
Career_Companion/
├── app.py                        # Streamlit entry point and navigation
├── requirements.txt              # Python dependencies
├── .env.example                  # Safe local environment template
├── .gitignore
├── .streamlit/
│   ├── config.toml               # Streamlit theme/server settings
│   └── secrets.toml.example      # Safe deployment secrets template
├── alembic.ini
├── docs/
│   └── screenshots/              # UI screenshots referenced in README
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
│   ├── config.py                 # Settings and configuration precedence
│   ├── database.py               # Engine, sessions, schema initialization
│   ├── models.py                 # SQLAlchemy entities
│   ├── schemas.py                # Structured request/response schemas
│   ├── services/                 # Applications, learning, AI, documents, etc.
│   │   ├── application_service.py
│   │   ├── backup_service.py
│   │   ├── document_service.py
│   │   ├── endpoint.py
│   │   ├── firecrawl_service.py
│   │   ├── insights_service.py
│   │   ├── learning_service.py
│   │   ├── ollama_service.py
│   │   ├── ollama_transport.py
│   │   └── request_guard.py
│   └── ui/                       # Nine Streamlit page modules and helpers
├── tests/                        # pytest test suite
├── deploy/
│   └── Caddyfile.example         # Optional secured self-hosted Ollama proxy
├── DEPLOYMENT.md
└── VALIDATION.md
```

The repository also includes a demo-data service (`src/services/demo_service.py`) and additional UI files. A full README should remain the entry point; implementation details live in the source modules.

## Quick start

### Requirements

- **Python 3.12** is recommended by the project's deployment notes. Use a compatible version supported by the pinned Streamlit release.
- Git and Python `pip`.
- **Optional:** Ollama installed locally if you want local AI, or an Ollama Cloud account and API key for hosted inference.
- **Optional:** A PostgreSQL database if you want to run locally against the same storage type as production.

### 1. Clone the project

```bash
git clone <YOUR_REPOSITORY_URL>
cd Career_Companion
```

Replace `<YOUR_REPOSITORY_URL>` with the actual public or private Git repository URL. If you downloaded the source as a ZIP, extract it and open a terminal beside `app.py`.

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
```

Linux / macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Configure a local environment

Copy `.env.example` to `.env` and edit it. For the simplest **local-only** setup:

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

The explicit `APP_ENV=local` setting is important: if omitted, the application deliberately defaults to protected cloud mode. Local authentication bypass is **for a trusted personal computer only**, not an Internet-facing deployment.

For local Ollama inference, make sure Ollama is running and the model is available:

```bash
ollama pull qwen2.5:0.5b
ollama list
```

Start the Ollama server only if it is not already running (desktop Ollama may start it automatically):

```bash
ollama serve
```

### 5. Start the application

```bash
python -m streamlit run app.py
```

Open **<http://localhost:8501>**. The entry point calls `init_db()`, which creates missing SQLAlchemy tables. The repository also contains Alembic migrations; for an existing database already managed by Alembic, use the appropriate migration workflow rather than assuming `create_all()` upgrades every existing column.

### Use Ollama Cloud from a locally running Streamlit app

You can keep Streamlit in local mode and run the AI remotely. In your local **untracked** `.env`, change only the AI settings:

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

`beam:cloud` is the model shown in the supplied deployed screenshots; check the current Ollama cloud catalog and your account's model access before using any specific name. A model downloaded with `ollama pull` on your PC does **not** automatically exist on Ollama Cloud.

## Configuration

### Where each setting belongs

| Location | Use | Commit to Git? |
| --- | --- | --- |
| `.env` | Local machine runtime values | **No** |
| `.env.example` | Variable names and harmless placeholders | Yes |
| `.streamlit/config.toml` | Theme, UI, and Streamlit server options | Yes |
| `.streamlit/secrets.toml` | Local Streamlit secrets, if needed | **No** |
| Streamlit Cloud **Settings -> Secrets** | Production DB, OAuth, and API credentials | Not stored in the repository |

The inspected code resolves settings in this order: **Streamlit Secrets -> process environment -> local `.env` -> built-in defaults**. The cloud configuration locks the saved Ollama endpoint and model to environment-managed values, preventing old local settings from silently overriding deployment settings.

### Common environment variables

| Variable | Description | Example or default |
| --- | --- | --- |
| `APP_ENV` | Selects local or protected cloud mode | `local` or `cloud` |
| `AUTH_REQUIRED` | Enables local sign-in when explicitly requested | `false` in local mode |
| `OWNER_EMAIL` | Exact verified Google email allowed in hosted workspace | `owner@example.com` |
| `DATABASE_URL` | SQLite or PostgreSQL connection string | `sqlite:///data/career_companion.db` |
| `AI_PROVIDER` | Ollama provider selection | `ollama` |
| `OLLAMA_BASE_URL` | Ollama HTTP base URL | Local: `http://localhost:11434`; Cloud: `https://ollama.com` |
| `OLLAMA_API_KEY` | Bearer token for hosted Ollama/secured proxy | Secret, never commit |
| `OLLAMA_MODEL` | Model available at that endpoint | Local: `qwen2.5:0.5b`; cloud example: `beam:cloud` |
| `OLLAMA_NUM_CTX` | Requested model context budget | Default `4096` |
| `OLLAMA_OUTPUT_TOKENS` | Requested Detailed-mode output budget | Default `700` |
| `OLLAMA_CONNECT_TIMEOUT` | Connection timeout, seconds | `5` |
| `OLLAMA_FIRST_TIMEOUT` | First-answer timeout, seconds | `120` |
| `OLLAMA_IDLE_TIMEOUT` | Streaming idle timeout, seconds | `60` |
| `OLLAMA_TOTAL_TIMEOUT` | Overall model request budget, seconds | `300` |
| `OLLAMA_KEEP_ALIVE` | Ollama keep-alive preference | `10m` |
| `FIRECRAWL_API_KEY` | Enables optional web retrieval | Blank disables it |
| `FIRECRAWL_TIMEOUT` | Search request timeout | `30` |
| `SEARCH_MAX_RESULTS` | Max web search results | `3` |
| `SEARCH_CACHE_TTL_SECONDS` | Search cache lifetime | `3600` |
| `APP_TIMEZONE` | Display timezone | `Europe/Bucharest` |
| `MAX_UPLOAD_SIZE_MB` | App-level per-document upload limit | `15` |
| `MAX_CONTEXT_CHARS` | Limit on assembled AI context text | `6000` |

**Output-length note:** In the inspected code, **Quick** mode caps generation at **512** tokens, while **Detailed** requests up to `OLLAMA_OUTPUT_TOKENS`. The configured output budget is also constrained to no more than half `OLLAMA_NUM_CTX`. Hitting a length limit can result in a preserved partial answer rather than a complete result.

### Example Streamlit Cloud Secrets

The sample below corresponds to the **flat `[auth]` configuration used by the inspected `st.login()` call**. Preserve the values already working for your instance and replace only placeholders on a new deployment.

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

FIRECRAWL_API_KEY = ""  # Optional
APP_TIMEZONE = "Europe/Bucharest"
MAX_UPLOAD_SIZE_MB = "15"

[auth]
redirect_uri = "https://YOUR-APP.streamlit.app/oauth2callback"
cookie_secret = "REPLACE_WITH_RANDOM_SECRET"
client_id = "YOUR_GOOGLE_OAUTH_CLIENT_ID"
client_secret = "YOUR_GOOGLE_OAUTH_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

**OAuth implementation detail:** The supplied `src/access.py` calls `st.login()` without a provider argument, so Google credentials appear directly beneath `[auth]`. If you change to a named `[auth.google]` provider, the corresponding application login call must also be updated to `st.login("google")`.

Never publish this file with real values or expose a PostgreSQL password, OAuth secret, or API key in issue reports or screenshots.

## Deploy your own instance

This walkthrough deploys an independent **single-owner** copy. The live `careercomp.streamlit.app` URL is not an invitation to register as another user.

1. **Push your own repository.** Ensure `app.py`, `src/`, `migrations/`, `requirements.txt`, and `.streamlit/config.toml` are tracked. Do not push `.env`, `.streamlit/secrets.toml`, `data/`, or backup ZIPs.
2. **Create a Neon PostgreSQL database.** Obtain a connection URI for its target branch. Use the pooled URI for app traffic; use a direct database URI when required by migrations or administrative operations. Require TLS (`sslmode=require` or provider-supplied stronger parameters).
3. **Create a Google OAuth web client.** In Google Cloud Console, configure the OAuth consent screen, test-user settings if applicable, and the exact authorized redirect URI: `https://YOUR-APP.streamlit.app/oauth2callback`.
4. **Create a Streamlit Cloud app.** Point it to your repository, deployed branch, and `app.py`. Use Python 3.12 where supported by the deployment configuration.
5. **Paste Secrets.** In **Manage app -> Settings -> Secrets**, set `OWNER_EMAIL`, `DATABASE_URL`, the `[auth]` configuration, and an authenticated HTTPS Ollama endpoint. Keep all top-level settings **above** `[auth]` in TOML.
6. **Choose AI hosting.** For Ollama Cloud use `OLLAMA_BASE_URL=https://ollama.com`, an Ollama Cloud API key, and an actual cloud-accessible model. For self-hosted Ollama, expose a protected HTTPS reverse proxy; do not directly expose an unauthenticated Ollama port.
7. **Save and reboot.** Verify Google sign-in, dashboard/database connectivity, a record that survives an app reboot, and **Settings -> Run Live Ollama & Model Check**.
8. **Test each relevant workflow.** Create an application, link an interview, save a note, upload/download a small document, generate a short AI answer, prepare a ZIP backup, and check the contents.

**Important:** Streamlit Cloud's temporary local filesystem should not be used as the only storage for job data or uploaded originals. The inspected cloud implementation uses PostgreSQL and stores newly uploaded document bytes in `DocumentContent` records.

## User guide

### 1. Sign in and use the Dashboard

On a cloud deployment, sign in with the Google account listed in `OWNER_EMAIL`. The **Dashboard** highlights your active work: applications, upcoming interviews, follow-ups, study tasks, and revisions. Use the quick-action buttons to jump to common tasks.

![Dashboard overview](docs/screenshots/dashboard.jpg)

### 2. Add a job application

Open **Applications -> Add New Application**. Enter the company and role, then complete useful optional details such as status, priority, source, location, job description, salary range, and job link. Save the application.

Use the application card's **Edit Record**, **Status History**, **Contacts & Tasks**, and **Archive / Delete** controls. Add a clear next action and due date—for example, *“Tailor CV to role requirements by Friday.”* An application left in **Saved** is not counted as submitted in conversion denominators.

![Job applications view](docs/screenshots/applications.jpg)

### 3. Prepare for an interview

Open **Interviews**, choose an application, and use **Log / Schedule Interview for This Application**. Record the interview type, date, participant details, and preparation checklist. Add topics to ask the interviewer and record feedback and reflection afterward.

Keep practice questions in the **Practice Bank** until you can confirm they were asked in an actual interview; use **Mark as Confirmed Asked in Interview** only when that is true.

![Interview preparation view](docs/screenshots/interviews.jpg)

### 4. Build your Experience Bank

Open **Experience Bank -> Add Entry to Experience Bank**. Record a real project, technical skill, measurable achievement, volunteering experience, or STAR story. Add relevant competency tags and supporting evidence. The assistant can then reference these facts instead of guessing your experience.

Use only facts and outcomes you can substantiate. Any fictional data loaded from the demo-data option is for experimentation, not personal portfolio claims.

![Experience Bank view](docs/screenshots/experience.jpg)

### 5. Upload a CV or study resource

Open **Documents -> Upload New Document or Version**. Set a title, document type, and version label, then choose a `.pdf`, `.docx`, `.txt`, or `.md` file. Select **Upload & Extract Text**.

After upload, check the extraction status. PDF extraction reads selectable text and retains page markers; scanned/image-only PDFs may be flagged as unreadable rather than silently treated as successful. You can preview extracted text and download the original file. The **application-enforced limit is 15 MB by default**, even if Streamlit's file picker displays a higher platform upload limit.

![Documents and Version Repository view](docs/screenshots/documents.jpg)

### 6. Create learning goals and log study

Open **Learning** to add topics and skills, create certification or job-preparation goals, attach resources, and log study sessions. Add notes and tasks, practice quizzes, and schedule revisions. Review quiz results and the evidence-based proficiency status. Confidence is self-reported and does not substitute for practice evidence.

![Learning Hub and Certification Prep view](docs/screenshots/learning.jpg)

### 7. Use the AI Assistant with specific context

Open **AI Assistant**. Select a mode and, where relevant, a job application, topic, learning goal, documents, notes, and Experience Bank records. Choose **My materials (no web search)** unless you specifically need web retrieval. Use **Quick** for shorter results and **Detailed** for longer answers.

For example, choose **Job analysis**, select an application, include relevant Experience Bank entries, and ask it to distinguish **required** and **preferred** skills and identify which ones are supported by recorded evidence. Review the answer before acting on it.

![Career and Learning Assistant view](docs/screenshots/assistant.jpg)

### 8. Review Insights

Open **Insights** to inspect application counts, response/interview/offer history, status and source distributions, frequently requested skills, study duration, and quiz results. The application warns about small samples; these are **historical descriptive statistics**, not predictions of the chance of getting a job.

![Insights and Progress Analytics view](docs/screenshots/insights.jpg)

### 9. Export and back up

Open **Settings -> Portability, Exports & Full Backups**. Use **Download Applications CSV** for a spreadsheet-friendly list or **Prepare Full Backup**, followed by **Download Full Backup (.zip)**, for an archive of the supported workspace data and original attachments.

To restore, use **Validate & Restore from Backup (.zip)**; review the non-destructive preview and confirm explicitly before replacing the current workspace. **Take a backup of the target workspace first.**

![Settings, Portability and Backups view](docs/screenshots/settings.jpg)

## AI assistant

### Available modes

| Mode | Typical use | Notes |
| --- | --- | --- |
| **Tutor** | Explain a concept at beginner, intermediate, or deep technical level | Can use selected reference materials and page citations when available |
| **Quiz** | Produce practice multiple-choice questions | User selects 1–5 questions; structured output is validated |
| **Mock interview** | Practice technical, behavioral STAR, or mixed interviews | Designed to ask one question at a time |
| **Answer coach** | Critique a draft interview answer | Instructed to avoid inventing achievements or metrics |
| **Job analysis** | Classify explicit role requirements and compare against experience | Separates required/preferred and missing/unknown evidence |
| **Study planner** | Suggest a study plan from goals and available weekly hours | Treat generated plans as drafts to review |

### Source and context options

- **My materials (no web search):** selected job, notes, documents, skills, goals, and Experience Bank entries.
- **Combine my materials + web:** includes selected personal context and attempts optional Firecrawl retrieval.
- **Search the web:** searches external sources when Firecrawl is configured; does not use selected private materials in that mode.

Web results are external, untrusted source data. A listed link does not guarantee that every AI claim was verified. Uploaded material and Experience Bank content are sent to the configured AI endpoint when selected, so avoid transmitting confidential material to a provider you do not trust.

### Ollama Cloud versus local Ollama

| | Local Ollama | Ollama Cloud |
| --- | --- | --- |
| Base URL | `http://localhost:11434` | `https://ollama.com` |
| Runtime | Your computer or separately hosted Ollama machine | Remote Ollama-hosted inference |
| API key | Usually none for loopback | Required for direct cloud API |
| Model selection | Must be installed on that Ollama host | Must be available to your cloud account |
| Streamlit Cloud compatibility | Requires separate authenticated HTTPS access | Direct HTTPS service connection |

A model from `ollama list` on your PC is **not** automatically available at `https://ollama.com`. The configured model must exist at the chosen endpoint. The included example `.env` defaults to a local Qwen model, while the provided deployment screenshots show `beam:cloud`.

### Output limits and partial responses

The inspected implementation uses a Quick cap of **512 output tokens**; Detailed uses the configured `OLLAMA_OUTPUT_TOKENS` value, subject to the model/context configuration. It also enforces a context-related ceiling and request timeouts. If the provider stops with a length-limit condition, the application labels the response as **incomplete**, retains the partial text, and can offer options to download or save it as an explicitly incomplete note.

Increase `OLLAMA_OUTPUT_TOKENS` and choose **Detailed** for longer responses, but don't assume that arbitrarily high limits guarantee completion. Smaller questions and context selections are often more reliable for structured outputs. The model can make mistakes, fabricate details, or fail a requested schema.

## Persistence, exports, and backups

### Database behavior

- **Local:** SQLite can store the workspace on a trusted machine.
- **Hosted:** `src/access.py` requires a PostgreSQL `DATABASE_URL`. `src/database.py` creates missing tables on startup, and the repository includes Alembic migrations for schema-managed environments.
- **Documents:** new original file bytes are stored in the database (`DocumentContent`), together with metadata/extracted text (`Document`). Legacy local attachments may still be read from `data/uploads/`.
- **Settings and chats:** user preferences, AI sessions/messages, applications, interviews, and learning information use SQLAlchemy records.

The backup service exports supported tables and attachment contents into a ZIP and excludes known secret settings. **The archive can still contain highly personal job information and text copied into notes or chats**. Treat it as sensitive and store it privately. Import validation previews the archive before a transaction-backed restore; an authorized restore **replaces** the target workspace's existing data.

Backups are not equivalent to provider-level point-in-time recovery. Maintain independent backup copies and test restoring to a disposable database before relying on them. Database provider storage limits and upload size constraints still apply.

## Security and privacy

- Cloud authentication verifies Google OIDC claims and allows access only when `email_verified` is true and the account email matches `OWNER_EMAIL` (case-insensitive).
- The application checks owner access before opening workspace data, but it is **not** designed to isolate data between multiple users or organizations.
- Store `DATABASE_URL`, `OLLAMA_API_KEY`, Firecrawl credentials, OAuth client secrets, and the cookie secret only in local untracked config or Streamlit Cloud Secrets.
- Do not commit `.env`, `.streamlit/secrets.toml`, `data/`, backups, or personal documents. The included `.gitignore` covers common private paths.
- If a secret was previously committed or shared, **rotate the credential**; removing it from the latest commit does not remove it from Git history.
- Hosted Ollama endpoints must use HTTPS with authorization. Do **not** publicly expose a local Ollama port without access control.
- Selected data is sent to the AI provider. Optional Firecrawl searches send web-search queries to an additional external service; review those providers' current data policies before sending sensitive content.
- An authenticated personal workspace is not proof of independent penetration testing, compliance certification, end-to-end encryption, or zero retention by service providers.

## Troubleshooting

| Symptom | Likely cause | What to check |
| --- | --- | --- |
| `ModuleNotFoundError: src.access` or `src.services.endpoint` | A source file exists locally but was never committed | `git status`, `git ls-files`, correct file paths/case, pushed branch |
| `Private workspace is locked` | Missing owner email or OIDC secrets | Set top-level `OWNER_EMAIL` and the matching `[auth]` configuration in **Streamlit Cloud Secrets** |
| Google `redirect_uri_mismatch` | Google OAuth web client has a different callback | Register the exact `https://YOUR-APP.streamlit.app/oauth2callback` URI |
| `Cloud mode requires ... PostgreSQL DATABASE_URL` | Cloud app is configured with SQLite or no DB URI | Set a persistent PostgreSQL URL in Streamlit Secrets |
| Database connection error | Incorrect URI/password, SSL mode, unreachable database, or missing driver | Verify Neon pooled URI, credentials, SSL parameters, and `psycopg[binary]` dependency |
| `Cloud mode cannot use localhost` | Hosted Streamlit cannot reach its own local machine's Ollama instance | Use Ollama Cloud or a separately hosted authenticated HTTPS Ollama endpoint |
| AI `authentication_error` | Incorrect, revoked, or missing remote Bearer API key | Check `OLLAMA_API_KEY` in the environment for the correct endpoint; never paste it into logs/issues |
| AI `model_not_found` | Model is absent from the configured Ollama host/account | Check exact `OLLAMA_MODEL` and the server's available model list; local installs do not exist on cloud automatically |
| AI `output_limit` | Generation stopped before completion | Use Detailed, increase a reasonable output cap, reduce prompt complexity; review the preserved partial answer |
| AI response times out | Remote model, network, or structured response took too long | Check live model diagnostics, timeout settings, model availability, and request complexity |
| Web search unavailable | Firecrawl key missing/invalid or request failed | Check optional `FIRECRAWL_API_KEY`, search usage and provider status; use materials-only mode meanwhile |
| Uploaded PDF has no extracted text | Scan/image PDF without selectable text | Supply a text-based PDF or extract text separately; this app does not claim OCR for scans |
| Backup upload rejected | Invalid archive, unsupported format, or archive constraints | Use the app's exported ZIP, review validation preview, and consult `DEPLOYMENT.md` |
| Local settings seem ignored | Environment or Streamlit Secrets override database-saved preferences | Check the configuration precedence and restart after changes |

For deployed crashes, open **Manage app -> Logs** on Streamlit Community Cloud and inspect the traceback, redacting secrets before sharing it.

## Testing

The repository includes pytest tests for application persistence and statuses, document/learning behavior, backup import/export, cloud configuration, Streamlit UI, Ollama transport/service, request guards, and optional web search.

Run from the directory containing `app.py` after installing requirements:

```bash
python -m pytest -q
```

For a local smoke test:

```bash
python -m streamlit run app.py
```

Then verify manually that you can (1) create an application; (2) link an interview; (3) save a study session; (4) upload and download a small document; (5) use **Run Live Ollama & Model Check**; (6) generate an answer; (7) save or export data; and (8) reboot the app and find the same records.

**Validation status for this README:** The source archive was inspected and screenshots were reviewed. An attempt to run `python -m pytest -q` in the documentation environment stopped during test collection because `streamlit` was **not installed** there (`ModuleNotFoundError`). No passing test count, complete browser test, or live deployment validation is claimed here. The owner has separately reported successful use of the deployed app and AI features; that is not a substitute for repeatable automated test results.

## Limitations and roadmap

### Current limitations

- **Single owner:** the hosted access check admits only one configured verified email; multi-user account isolation is not implemented.
- **External dependencies:** Ollama Cloud, Neon, Google OAuth, and optional Firecrawl have their own availability, model access, and quota constraints.
- **AI limits:** results depend on model capabilities and token budgets.
- **File limits:** permitted formats are `.txt`, `.md`, `.pdf`, and `.docx`, with an app-level 15 MB default; scanned PDFs lack built-in OCR.
- **Operational responsibility:** users must manage credentials, provider limits, migrations, backups, and any migration of preexisting SQLite records to PostgreSQL.

### Potential future improvements (not current features)

- Better onboarding and small guided tasks for a freshly deployed workspace.
- Optional scheduling/reminders for application follow-ups.
- Additional supported AI backends and model-specific settings.
- More detailed, sample-aware job-search analytics and CV/job comparison workflows.

## License and references

**License:** No license file was present in the inspected project archive. Do not assume public source code is automatically licensed for unrestricted redistribution. Add an appropriate license only when the repository owner chooses one.

**Contributions:** This is maintained primarily as a personal application. Check repository issues or contact the maintainer before undertaking significant changes; avoid submitting private credentials, personal backups, or real applicant data.

Official resources:

- [Streamlit documentation](https://docs.streamlit.io/)
- [Streamlit authentication](https://docs.streamlit.io/develop/concepts/connections/authentication)
- [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud)
- [Neon documentation](https://neon.com/docs)
- [SQLAlchemy documentation](https://docs.sqlalchemy.org/)
- [Alembic documentation](https://alembic.sqlalchemy.org/)
- [Ollama documentation](https://docs.ollama.com/)
- [Firecrawl documentation](https://docs.firecrawl.dev/)
- [Plotly Python documentation](https://plotly.com/python/)

---

*Documentation basis: supplied Career Companion cloud project archive, deployed application screenshots, and the current task description. If a later Git commit changes the configuration or behavior, update this README alongside the code.*
