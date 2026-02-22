# RAGMind

AI-powered requirements engineering platform that turns interview transcripts and project conversations into structured SRS drafts.

## What It Does
- Upload documents (PDF, DOCX, TXT) and extract raw transcript text.
- Ask project questions and get cited answers grounded in stored transcript text.
- Run guided interview sessions to collect complete requirement coverage.
- Generate versioned SRS drafts and export them to PDF.

## Current Architecture (Transcript-First)
- **Frontend:** Vanilla JS SPA (`frontend/`) with Arabic/English support.
- **Backend:** FastAPI (`backend/main.py`) with route/controller/service layers.
- **Storage:** PostgreSQL for projects, assets, chat messages, and SRS drafts.
- **LLM Providers:** Gemini, OpenRouter, Groq, Cerebras.
- **Flow:** Extract transcript text -> store in `assets.extracted_text` -> query/SRS from transcript context.

## Backend Structure
- `backend/routes/`: API endpoints (`projects`, `documents`, `query`, `interview`, `srs`, etc.)
- `backend/controllers/`: orchestration (`document_controller`, `query_controller`, `project_controller`)
- `backend/services/`: domain logic (`document_loader`, `answer_service`, `query_service`, `srs_service`, ...)
- `backend/database/models.py`: ORM models (`User`, `Project`, `Asset`, `ChatMessage`, `SRSDraft`)

## Key API Endpoints
- `POST /projects/{project_id}/documents` — upload document
- `POST /projects/{project_id}/query` — ask question (non-stream)
- `POST /projects/{project_id}/query/stream` — ask question (SSE stream)
- `POST /projects/{project_id}/srs/refresh` — generate new SRS draft
- `GET /projects/{project_id}/srs/export` — export draft as PDF
- `GET /health` — backend/database health

## Setup (Windows)
1. Copy environment template:
   - `copy .env.example .env`
2. Run setup:
   - `setup.bat`
3. Start Docker database:
   - `start_docker.bat`
4. Start backend/frontend:
   - `start_backend.bat`

Or use one-click startup:
- `start.bat`

## Environment Notes
Required:
- `DATABASE_URL`
- `GEMINI_API_KEY` (or another supported LLM provider key)

Optional:
- `GROQ_API_KEY` for speech-to-text routes
- `TELEGRAM_BOT_TOKEN` for Telegram bot integration

## Development Notes
- The project no longer uses vector databases or chunk/embedding pipelines.
- Query and SRS generation now operate on raw extracted transcript text.
- If PostgreSQL is not running, DB-dependent operations and tests will fail.
