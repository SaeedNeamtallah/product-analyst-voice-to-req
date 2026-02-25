# 📘 Tawasul (SpecWise AI) Documentation

**Version:** 1.0.0  
**Last Updated:** February 2026  
**Classification:** Technical Architecture & System Design (Confidential)

---

## 1) Vision

**Tawasul** is a voice-first AI agent platform that automates software requirement elicitation for non-technical stakeholders. It transforms free-form text/audio conversations into structured, evolving SRS outputs.

The platform is designed to:
- Reduce dependency on traditional manual requirement interviews.
- Extract requirements incrementally through intelligent clarification loops.
- Support Arabic (including Egyptian dialect) and English.
- Provide a unified workflow across web and Telegram channels.

---

## 2) Product Scope

Current product scope includes:
- User and project management.
- Interactive interview loop with continuously updated SRS drafts.
- Voice input through STT with post-processing correction.
- SRS export to HTML/PDF.
- Multi-session Telegram bot integration.

---

## 3) Tech Stack

### Backend
- Python 3.10+
- FastAPI (async)
- SQLAlchemy Async + asyncpg

### Data & Storage
- PostgreSQL (core entities)
- Local/S3 object storage for uploaded assets

### AI Layer
- LLM Factory with multiple providers:
  - Gemini
  - OpenRouter
  - Groq
  - Cerebras
- STT providers:
  - Groq Whisper
  - OpenAI Whisper
- LLM post-processing for STT cleanup

### Frontend & Channels
- Vanilla JavaScript + HTML + CSS
- Telegram bot (pyTelegramBotAPI)

---

## 4) High-Level Architecture

The system is implemented as a **modular monolith**, with a clear path to service decomposition when scaling requires it.

### Core Layers
1. **API Layer (FastAPI Routers)**
   - auth, projects, documents, query, interview, stt, srs, messages, judge, stats, health, handoff
2. **Service Layer**
   - interview orchestration, SRS lifecycle, resilience/failover, telemetry, locking
3. **Provider Layer**
   - LLM provider factory + OpenAI-compatible providers
4. **Persistence Layer**
  - PostgreSQL models (single source of truth)
5. **Channel Layer**
   - Web client + Telegram bot sharing the same backend business logic

---

## 5) Core Modules

### 5.1 Interview Orchestrator
**File:** `backend/services/interview_service.py`

- Core analytical and orchestration engine.
- Drives stateful interview progression through stages:
  - discovery
  - scope
  - users
  - features
  - constraints
- Uses patch-like partial updates to SRS drafts instead of full rewrites.
- Integrates resilient multi-provider LLM execution with failover.

### 5.2 LLM Provider Factory
**File:** `backend/providers/llm/factory.py`

- Decouples business logic from a single LLM vendor.
- Selects providers dynamically based on configuration and key availability.
- Supports fallback behavior through `run_with_failover` patterns.

### 5.3 STT Pipeline
**File:** `backend/routes/stt.py`

Processing flow:
1. Receive audio input.
2. Transcribe audio via Whisper provider.
3. Pass raw transcript to an LLM post-processor (low temperature) for cleanup.
4. Return cleaned text into the interview flow.

### 5.4 Document Processing
**Files:**
- `backend/routes/documents.py`
- `backend/services/file_service.py`

- Upload and manage project-linked assets.
- Extract text from supported document formats.
- Support local or S3-backed storage.

### 5.5 Telegram Multi-Session Bot
**Files:**
- `telegram_bot/bot.py`
- `telegram_bot/handlers.py`

- Adds a production channel fully integrated with backend flows.
- Uses local instance locking to prevent duplicate bot processes on one machine.

---

## 6) Data Workflow

### A) Elicitation Loop
1. **Input**: user text or voice.
2. **(Optional) STT Cleanup**: normalize noisy transcript output.
3. **Context**: load latest SRS draft + chat history.
4. **LLM Turn**: generate clarification response + state updates.
5. **Persist**: store chat turn and update draft/version.
6. **Return**: deliver next prompt/question to continue elicitation.

### B) SRS Export Loop
1. Aggregate final structured draft content.
2. Apply engineering-style formatting.
3. Generate HTML then PDF.

---

## 7) Database Schema Highlights

**Reference file:** `backend/database/models.py`

Primary tables in the current implementation:
- `users`: authentication and user profile data
- `projects`: top-level container for requirement elicitation lifecycle
- `assets`: uploaded documents and processing status
- `chat_messages`: project-level conversation history
- `srs_drafts`: versioned SRS draft snapshots

> Note: Some older design artifacts may reference logical entities such as `Requirement` or `Document`. In the current codebase, those concerns are represented through `srs_drafts` and `assets`.

---

## 8) Reliability & Resilience

### Failover
- LLM/STT calls support automatic fallback across configured providers.
- If one provider fails or is rate-limited, execution shifts to alternatives.

### Backend-managed State
- Runtime and interview state are persisted in PostgreSQL.
- This avoids cross-worker drift and removes external cache coupling.

### Observability
- Middleware injects `X-Request-ID` and `X-Response-Time-ms`.
- `/metrics` endpoint is Prometheus-compatible when enabled.

---

## 9) Risk Matrix (Compact FMEA)

| Domain | Risk | Mitigation Strategy |
|---|---|---|
| Interview State | Concurrent update collisions | PostgreSQL row locking + backend-managed state |
| LLM Quality | Hallucination or over-generalization | Incremental update style + context grounding + low temperature where needed |
| STT Accuracy | Dialect/noise/transcription drift | Post-processing layer before downstream analysis |
| Provider Availability | Single-vendor outage | Multi-provider failover |
| Runtime Consistency | Worker state divergence | DB-backed state and transactional updates |

---

## 10) Local Runbook

### Prerequisites
- Python 3.10+
- Docker Desktop
- PowerShell (Windows)

### Quick Start
- Start everything: `start.bat`
- Start Docker services only: `start_docker.bat`
- Start backend: `start_backend.bat`
- Start Telegram bot: `start_telegram_bot.bat`

### Current Docker Services
**File:** `docker-compose.yml`
- PostgreSQL on host port `5555` (default)

---

## 11) Environment Variables

Baseline example:

```env
# Core
DATABASE_URL=postgresql+asyncpg://tawasul:tawasul123@localhost:5555/tawasul

# LLM / STT
LLM_PROVIDER=gemini
GEMINI_API_KEY=...
OPENROUTER_API_KEY=...
GROQ_API_KEY=...
CEREBRAS_API_KEY=...
OPENAI_API_KEY=...

# App
API_HOST=127.0.0.1
API_PORT=8500
ENVIRONMENT=development
JWT_SECRET=...

# Telegram
TELEGRAM_BOT_TOKEN=...
```

> Full supported configuration keys are defined in `backend/config.py`.

---

## 12) Main REST Surface

- Health: `/health`
- Auth: `/auth/*`
- Projects: `/projects/*`
- Documents: `/projects/{project_id}/documents*`
- Interview: `/interview/*`
- STT: `/stt/*`
- SRS: `/srs/*`
- Metrics: `/metrics`

> See `backend/main.py` for the currently enabled router list.

---

## 13) Project Structure (Condensed)

```text
backend/
  main.py
  config.py
  database/
    models.py
  routes/
    auth.py, projects.py, documents.py, query.py, interview.py, stt.py, srs.py, ...
  services/
    interview_service.py, srs_service.py, stt_service.py, resilience_service.py, ...
  providers/llm/
    factory.py, gemini_provider.py, openai_compat_provider.py, ...
frontend/
  index.html, app.js, style.css
telegram_bot/
  bot.py, handlers.py, config.py
docker-compose.yml
start*.bat
```

---

## 14) Important Architecture Notes

- This repository reflects a product-oriented implementation with clear extensibility points.
- Some earlier presentations may mention Qdrant or separate RAG services; the current active path is centered on:
  - PostgreSQL (single source of truth)
  - Document extraction + conversational elicitation
  - LLM/STT failover
- Future RAG/vector capabilities can be added as an additional layer on top of the existing interview orchestration.

---

## 15) Suggested Engineering Roadmap

1. Formalize migration workflows (stronger Alembic + CI checks).
2. Expand integration tests for interview/STT critical paths.
3. Introduce worker queue isolation for heavy document processing.
4. Unify distributed tracing (OpenTelemetry) across key paths.
5. Publish deeper OpenAPI consumer documentation.

---

## 16) Executive Summary

**Tawasul** is not just a chatbot; it is an **agentic requirements platform** combining:
- multi-stage requirement elicitation,
- practical Arabic voice processing,
- resilient multi-provider AI execution,
- and fast local operability with enterprise growth potential.

This document serves as a single technical reference for engineering teams, technical leadership, and investment stakeholders.
