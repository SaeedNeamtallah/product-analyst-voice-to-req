# RAGMind

**AI-Powered Requirements Engineering Platform**

RAGMind transforms unstructured project conversations and documents into structured, exportable Software Requirements Specifications (SRS). It combines document-grounded Q&A with a guided interview agent that acts as a senior business analyst.

---

## Problem

Requirements gathering in software projects is ad-hoc, unstructured, and lossy. Teams lose critical details between stakeholder conversations and formal documentation. The gap between "what the client said" and "what got written down" causes scope creep, missed features, and failed projects.

## Solution

RAGMind provides three integrated capabilities:

1. **Document-Grounded Q&A** -- Upload project documents (PDF, DOCX, TXT), ask questions, and get answers with inline source citations via RAG.
2. **AI Business Analyst Interview** -- A guided interview agent that validates answers, detects contradictions, challenges vague requirements, and tracks coverage across 5 requirement areas (Discovery, Scope, Users, Features, Constraints).
3. **Automated SRS Generation** -- Converts conversation evidence into a structured SRS document with export to PDF.

---

## Architecture

### Pattern: Modular Monolith (Layered)

Single FastAPI application with clear route/controller/service/provider separation.

```
User (Browser :3000)
  |
  v
Frontend (Vanilla JS SPA, Arabic RTL + English)
  |  fetch() / SSE (EventSource)
  v
FastAPI Backend (:8500)
  |
  +-- Routes (13 modules)         -- HTTP endpoints, Pydantic validation
  |     |
  +-- Controllers (3)             -- Orchestration layer
  |     |
  +-- Services (10)               -- Domain logic, prompt engineering, RAG pipeline
  |     |
  +-- Providers                   -- Abstract interfaces + factory pattern
  |     +-- LLM (Gemini, OpenRouter, Groq, Cerebras)
  |     +-- Embedding (Cohere, Voyage, Gemini, BGE-M3)
  |     +-- VectorDB (pgvector, Qdrant)
  |
  v
Infrastructure:
  - PostgreSQL 16 + pgvector   (relational data + vector search)
  - Qdrant                      (optional dedicated vector DB)
  - Google Gemini API            (primary LLM)
  - Cohere / Voyage API          (embeddings)
  - Groq Whisper API             (speech-to-text)
```

### AI Agents (Prompted Components)

| # | Agent | Source | Purpose |
|---|---|---|---|
| 1 | RAG Answer Agent | `services/answer_service.py` | Context-grounded answers with inline citations |
| 2 | No-Context Fallback Agent | `services/answer_service.py` | General knowledge mode when no documents exist |
| 3 | Query Rewrite Agent | `services/query_service.py` | Optimizes queries for semantic retrieval |
| 4 | Interview BA Agent | `services/interview_service.py` | Validates, challenges, tracks 5 coverage areas, outputs JSON |
| 5 | Suggested Answers Agent | `services/interview_service.py` | Generates 3-5 candidate answers per question |
| 6 | SRS Generator Agent | `services/srs_service.py` | Converts conversation to structured SRS JSON |

### Agent Orchestration

- **Query pipeline:** Rewrite (optional) -> Embed -> Retrieve top-k -> Answer (or fallback)
- **Interview pipeline:** Dynamic slot-filling state machine -- on each turn the agent runs: rule-based constraint validation -> conversation reflection -> BA prompt (generates question + fills SRS JSON slots) -> cumulative summary/coverage merge -> live document patch -> suggested answers. The SRS JSON is populated continuously during the conversation, not generated at the end.
- **SRS pipeline:** Read full chat history -> Generate structured JSON -> Persist versioned draft -> Export PDF

---

## Folder Structure

```
RAGMind/
|-- backend/
|   |-- main.py                    # FastAPI app entry point + middleware
|   |-- config.py                  # Pydantic settings (reads .env)
|   |-- runtime_config.py          # Runtime-mutable configuration
|   |-- errors.py                  # Database error detection helpers
|   |-- init_database.py           # Schema creation + default admin
|   |-- requirements.txt           # Python dependencies
|   |
|   |-- database/
|   |   |-- connection.py          # Async SQLAlchemy engine + session factory
|   |   |-- models.py             # ORM models: User, Project, Asset, Chunk, ChatMessage, SRSDraft
|   |
|   |-- routes/                    # API endpoint handlers (13 modules)
|   |   |-- auth.py               # JWT register/login/me
|   |   |-- projects.py           # Project CRUD
|   |   |-- documents.py          # Document upload + processing
|   |   |-- query.py              # RAG query + streaming (SSE)
|   |   |-- interview.py          # Guided interview endpoints
|   |   |-- messages.py           # Chat message persistence
|   |   |-- srs.py                # SRS generation + export
|   |   |-- stats.py              # System statistics
|   |   |-- health.py             # Health check
|   |   |-- app_config.py         # AI/retrieval settings
|   |   |-- bot_config.py         # Telegram bot config
|   |   |-- stt.py                # Speech-to-text
|   |   |-- handoff.py            # Requirements handoff
|   |
|   |-- controllers/               # Business logic orchestration
|   |   |-- query_controller.py    # Query + answer pipeline
|   |   |-- project_controller.py  # Project operations
|   |   |-- document_controller.py # Document processing pipeline
|   |
|   |-- services/                  # Core domain logic
|   |   |-- interview_service.py   # Interview BA agent (orchestrator, prompts, coverage)
|   |   |-- answer_service.py      # RAG answer generation
|   |   |-- query_service.py       # Query processing + vector search
|   |   |-- srs_service.py         # SRS generation from chat history
|   |   |-- embedding_service.py   # Vector embedding management
|   |   |-- chunking_service.py    # Text chunking strategies
|   |   |-- document_loader.py     # PDF/DOCX/TXT parsing
|   |   |-- file_service.py        # File upload/storage
|   |   |-- stt_service.py         # Speech-to-text (Groq Whisper)
|   |   |-- constraints_checker.py # Dynamic slot-filling state machine
|   |   |-- telemetry_service.py   # Interview quality metrics (DB-backed)
|   |   |-- agent_telemetry.py     # In-memory agent metrics
|   |   |-- live_patch_service.py  # Live SRS patch builder
|   |
|   |-- providers/                 # Abstracted external integrations
|       |-- llm/
|       |   |-- interface.py       # Abstract LLM interface
|       |   |-- factory.py         # LLM provider factory
|       |   |-- gemini_provider.py
|       |   |-- openai_compat_provider.py  # OpenRouter, Groq, Cerebras
|       |   |-- cohere_provider.py
|       |   |-- voyage_provider.py
|       |   |-- hf_bge_m3_provider.py
|       |-- vectordb/
|           |-- interface.py       # Abstract VectorDB interface
|           |-- factory.py         # VectorDB provider factory
|           |-- pgvector_provider.py
|           |-- qdrant_provider.py
|
|-- frontend/
|   |-- index.html                 # SPA entry point (Arabic RTL + English)
|   |-- app.js                     # Application state + DOM logic
|   |-- style.css                  # Styling (light/dark themes)
|   |-- favicon.svg
|
|-- telegram_bot/                  # Optional Telegram integration
|   |-- bot.py
|   |-- handlers.py
|   |-- config.py
|
|-- docker-compose.yml             # PostgreSQL + Qdrant services
|-- init-db.sql                    # pgvector extension creation
|-- start_backend.ps1              # Primary startup script (Windows)
|-- start_backend.bat              # Startup wrapper
|-- .env.example                   # Environment template
```

---

## Diagrams

### Activity Diagram -- The Consultant Flow

The primary user journey is interview-first. Documents are optional context, not a prerequisite.

```mermaid
flowchart TD
    A[Login / Register] --> B[Start New Idea]
    B --> C[Interview: AI Business Analyst]
    C --> D[Agent Fills SRS Slots Continuously]
    D --> E{Coverage >= 70%?}
    E -->|No| C
    E -->|Yes| F[Generate SRS Draft]
    F --> G[Review & Edit SRS]
    G --> H[Schedule Handoff Meeting]

    B -.->|Optional| I[Upload Documents]
    I --> J[Extract -> Chunk -> Embed -> Index]
    J --> K[Chat: Ask Questions with Citations]
    K -.-> C
```

### Sequence Diagram -- RAG Query Flow

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Frontend
    participant API as FastAPI
    participant VDB as Vector DB
    participant DB as PostgreSQL
    participant LLM as LLM Provider

    U->>UI: Ask question
    UI->>API: POST /projects/{id}/query/stream
    API->>VDB: Search similar chunks (top-k)
    VDB-->>API: Chunk candidates + scores
    API->>LLM: Prompt (query + context)
    LLM-->>API: Stream tokens
    API-->>UI: SSE tokens + sources
    UI->>API: POST /projects/{id}/messages
    API->>DB: Insert chat messages
    DB-->>API: Commit OK
    API-->>UI: Success
```

### Data Model

```mermaid
classDiagram
    class User {
        +int id
        +string name
        +string email
        +string password_hash
        +string role
        +datetime created_at
    }

    class Project {
        +int id
        +string name
        +string description
        +json metadata
        +datetime created_at
        +datetime updated_at
    }

    class Asset {
        +int id
        +int project_id
        +string filename
        +string file_type
        +string status
        +json metadata
    }

    class Chunk {
        +int id
        +int project_id
        +int asset_id
        +text content
        +int chunk_index
        +json embedding
        +json metadata
    }

    class ChatMessage {
        +int id
        +int project_id
        +string role
        +text content
        +json metadata
        +datetime created_at
    }

    class SRSDraft {
        +int id
        +int project_id
        +int version
        +string status
        +string language
        +json content
    }

    Project "1" --> "*" Asset
    Project "1" --> "*" Chunk
    Project "1" --> "*" ChatMessage
    Project "1" --> "*" SRSDraft
    Asset "1" --> "*" Chunk
```

---

## Setup Instructions

### Prerequisites

- Python 3.8+
- Docker Desktop
- API keys: Gemini (required), Cohere or Voyage (for embeddings)
- **Optional for PDF exports:**
  - `cairosvg` Python package (`pip install cairosvg`)
  - Mermaid CLI (`npm install -g @mermaid-js/mermaid-cli` or download from https://github.com/mermaid-js/mermaid-cli)

  Without these the service will include raw Mermaid source text instead of rendered diagrams.

### Quick Start (Windows)

```powershell
# 1. Clone the repository
git clone <repo-url>
cd RAGMind---EELU-Project

# 2. Copy environment template and add your API keys
copy .env.example .env
# Edit .env with your actual API keys

# 3. Run the startup script
.\start_backend.bat
```

The startup script handles:
- Starting Docker services (PostgreSQL + Qdrant)
- Creating Python virtual environment
- Installing dependencies
- Initializing the database
- Starting frontend server on `http://localhost:3000`
- Starting backend API on `http://127.0.0.1:8500`

### Manual Setup

```powershell
# 1. Start infrastructure
docker-compose up -d

# 2. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Initialize database
python backend/init_database.py

# 5. Start backend
uvicorn backend.main:app --host 127.0.0.1 --port 8500 --reload

# 6. Start frontend (separate terminal)
python -m http.server 3000 --directory frontend
```

### Services

| Service | URL | Purpose |
|---|---|---|
| Frontend | `http://localhost:3000` | Web UI |
| Backend API | `http://127.0.0.1:8500` | REST API |
| API Docs | `http://127.0.0.1:8500/docs` | Swagger/OpenAPI |
| PostgreSQL | `localhost:5555` | Database |
| Qdrant | `localhost:6333` | Vector DB (optional) |

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

### Required

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL async connection string | `postgresql+asyncpg://ragmind:ragmind123@localhost:5555/ragmind` |
| `GEMINI_API_KEY` | Google Gemini API key | -- |
| `JWT_SECRET` | Secret for JWT token signing. Auto-generated if unset. | *(random per session)* |

### LLM Configuration

| Variable | Description | Default |
|---|---|---|
| `LLM_PROVIDER` | Active LLM provider | `gemini` |
| `GEMINI_MODEL` | Gemini model name | `gemini-2.5-flash` |
| `EMBEDDING_PROVIDER` | Embedding provider (`gemini`, `cohere`, `voyage`, `bge-m3`) | `gemini` |
| `COHERE_API_KEY` | Cohere API key (for embeddings) | -- |
| `VOYAGE_API_KEY` | Voyage AI API key (for embeddings) | -- |
| `OPENROUTER_API_KEY` | OpenRouter API key (for multi-model access) | -- |
| `GROQ_API_KEY` | Groq API key (for fast inference + Whisper STT) | -- |
| `CEREBRAS_API_KEY` | Cerebras API key | -- |

### Vector Database

| Variable | Description | Default |
|---|---|---|
| `VECTOR_DB_PROVIDER` | Vector DB backend (`pgvector` or `qdrant`) | `pgvector` |
| `QDRANT_URL` | Qdrant server URL | `http://localhost:6333` |

### Retrieval Tuning

| Variable | Description | Default |
|---|---|---|
| `CHUNK_SIZE` | Text chunk size (tokens) | `1000` |
| `CHUNK_OVERLAP` | Overlap between chunks | `200` |
| `CHUNK_STRATEGY` | Chunking strategy (`simple` or `parent_child`) | `parent_child` |
| `RETRIEVAL_TOP_K` | Number of chunks to retrieve | `5` |
| `RETRIEVAL_HYBRID_ENABLED` | Enable hybrid vector+lexical search | `false` |
| `RETRIEVAL_RERANK_ENABLED` | Enable reranking of results | `false` |
| `QUERY_REWRITE_ENABLED` | Enable LLM query rewriting | `false` |

### Other

| Variable | Description | Default |
|---|---|---|
| `CORS_ORIGINS` | Allowed CORS origins (JSON array) | `["http://localhost:3000", "http://localhost:8500"]` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `MAX_FILE_SIZE_MB` | Maximum upload file size | `50` |
| `JWT_EXPIRY_HOURS` | JWT token expiry | `72` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token (optional) | -- |

---

## API Reference

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login (returns JWT) |
| GET | `/auth/me` | Get current user info |

### Projects

| Method | Endpoint | Description |
|---|---|---|
| GET | `/projects` | List all projects |
| POST | `/projects` | Create project |
| GET | `/projects/{id}` | Get project details |
| PUT | `/projects/{id}` | Update project |
| DELETE | `/projects/{id}` | Delete project |

### Documents

| Method | Endpoint | Description |
|---|---|---|
| POST | `/projects/{id}/documents` | Upload document(s) |
| GET | `/projects/{id}/documents` | List project documents |
| DELETE | `/projects/{id}/documents/{doc_id}` | Delete document |

### RAG Query

| Method | Endpoint | Description |
|---|---|---|
| POST | `/projects/{id}/query/stream` | Stream answer via SSE |
| POST | `/projects/{id}/query` | Non-streaming answer |

### Chat Messages

| Method | Endpoint | Description |
|---|---|---|
| POST | `/projects/{id}/messages` | Persist chat message |
| GET | `/projects/{id}/messages` | List messages |
| DELETE | `/projects/{id}/messages` | Clear chat history |

### Interview

| Method | Endpoint | Description |
|---|---|---|
| POST | `/projects/{id}/interview/next` | Get next interview question |
| GET | `/projects/{id}/interview/draft` | Load saved interview state |
| POST | `/projects/{id}/interview/draft` | Save interview progress |
| DELETE | `/projects/{id}/interview/draft` | Clear saved interview |
| GET | `/projects/{id}/interview/telemetry` | Get interview quality metrics |

### SRS

| Method | Endpoint | Description |
|---|---|---|
| GET | `/projects/{id}/srs` | Get current SRS draft |
| POST | `/projects/{id}/srs/refresh` | Regenerate SRS from messages |
| GET | `/projects/{id}/srs/export` | Export SRS as PDF |

### Configuration

| Method | Endpoint | Description |
|---|---|---|
| GET | `/config/providers` | Get available AI providers |
| POST | `/config/providers` | Update AI configuration |
| GET | `/health` | Health check |
| GET | `/stats` | System statistics |

### Speech-to-Text

| Method | Endpoint | Description |
|---|---|---|
| POST | `/stt/transcribe` | Upload audio for transcription |

---

## Deployment Strategy

### Development (Current)

- PowerShell script starts Docker services + Python processes
- Frontend served via Python `http.server` (not production-ready)
- Hot reload enabled for backend via Uvicorn `--reload`

### Production (Recommended)

```yaml
# docker-compose.prod.yml
services:
  postgres:
    image: pgvector/pgvector:pg16
    # ... (same as dev)

  qdrant:
    image: qdrant/qdrant:latest
    # ... (same as dev)

  backend:
    build: ./backend
    command: uvicorn backend.main:app --host 0.0.0.0 --port 8500 --workers 4
    environment:
      - DATABASE_URL=postgresql+asyncpg://ragmind:${DB_PASSWORD}@postgres:5432/ragmind
    depends_on:
      postgres:
        condition: service_healthy

  frontend:
    image: nginx:alpine
    volumes:
      - ./frontend:/usr/share/nginx/html:ro
    ports:
      - "80:80"
```

**Production checklist:**
- [ ] Generate strong `JWT_SECRET` (e.g., `openssl rand -hex 32`)
- [ ] Set `CORS_ORIGINS` to actual frontend domain
- [ ] Use secrets management for API keys (not `.env` files)
- [ ] Set up PostgreSQL backups (pg_dump cron or managed DB)
- [ ] Put Nginx or Caddy in front for TLS termination
- [ ] Set `LOG_LEVEL=WARNING` in production
- [ ] Configure rate limiting at reverse proxy or application level
- [ ] Monitor LLM API costs and set budget alerts

---

## Technical Debt & Known Limitations

### Priority 0 -- Security

| Issue | Status |
|---|---|
| Interview routes lack authentication | **Fixed** -- `Depends(get_current_user)` on all endpoints |
| No project-level authorization (user ownership) | **Fixed** -- `user_id` FK on Project, all queries scoped |
| Wildcard CORS in development mode | **Fixed** -- uses `settings.cors_origins` |
| Default JWT secret must be changed for production | **Fixed** -- auto-generates random secret if unset |
| No rate limiting on LLM-calling endpoints | Open |

### Priority 1 -- Stability

| Issue | Status |
|---|---|
| Zero automated test coverage | Open |
| Alembic installed but not configured for migrations | Open |
| Double-commit behavior in `get_db()` session management | **Fixed** -- auto-commit removed, explicit commits in routes |
| Health endpoint doesn't check external service connectivity | **Fixed** -- checks PostgreSQL + Qdrant, reports degraded status |

### Priority 2 -- Maintainability

| Issue | Status |
|---|---|
| `interview_service.py` is a 72KB god file | Open |
| `app.js` is a 160KB monolith (no module system) | Open |
| No structured logging or request tracing | Open |
| No prompt injection protection on LLM inputs | Open |

---

## Roadmap

### Phase 1 -- Core Flow & Product Identity
- ~~Make interview mode the primary user flow~~ **Done** -- interview-first on all project entry points
- Auto-detect browser language on first visit
- Add auto-save for interview state on each turn
- ~~Add authentication to all routes~~ **Done**
- ~~Fix CORS and JWT defaults~~ **Done**

### Phase 2 -- Production Hardening
- ~~Add project ownership model (user_id FK)~~ **Done**
- ~~Fix double-commit in session management~~ **Done**
- ~~Add health checks for external services~~ **Done**
- Configure Alembic migrations
- Add basic test suite (auth, CRUD, interview state)
- Add per-user rate limiting and token budgets

### Phase 3 -- Scalability
- Containerize backend with Dockerfile
- Add async task queue for document processing
- Implement LLM response caching
- Multiple Uvicorn workers behind reverse proxy

### Phase 4 -- Product Depth & Enterprise
- Add inline SRS section editing
- Add version diff for SRS iterations
- Document deduplication detection
- Multi-tenant organization model
- Role-based access control (RBAC)
- Audit logging
- SSO integration (SAML/OIDC)
- Structured observability (Prometheus metrics, request tracing)

---

## License

See [LICENSE](./LICENSE) for details.
