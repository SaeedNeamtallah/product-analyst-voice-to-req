# RAGMind - AI Business Analyst & Document Intelligence Platform

![Project Status](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.68%2B-green)
![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-orange)
![License](https://img.shields.io/badge/License-MIT-purple)

**RAGMind** is an enterprise-grade platform that combines **Retrieval-Augmented Generation (RAG)** with an **AI Business Analyst** agent. It transforms static documents into interactive knowledge bases while providing guided requirements gathering, SRS generation, and project handoff capabilities for B2B SaaS workflows.

Built for the **EELU University Project**, this system bridges the gap between raw data and actionable intelligence.

---

## Key Features

### Core RAG Pipeline
- **Multi-format document support** - PDF, DOCX, TXT upload with drag-and-drop
- **Smart chunking** - Parent-child chunking strategy with configurable sizes
- **Multi-provider embeddings** - Gemini, Cohere, Voyage AI, BGE-M3 (HuggingFace)
- **Hybrid vector search** - pgvector and Qdrant with optional reranking
- **Streaming AI answers** - Server-Sent Events (SSE) with source citations

### AI Business Analyst
- **Guided interview mode** - 5-stage requirements gathering (discovery, scope, users, features, constraints)
- **Co-pilot split-screen** - Live document panel updates alongside chat conversation
- **SRS generation** - Auto-generate Software Requirements Specification from conversations
- **PDF export** - Export SRS documents with bilingual support
- **Project handoff** - Package SRS + conversation summary for engineering teams

### Voice & Multilingual
- **Speech-to-text** - Groq Whisper integration supporting 18 languages
- **Microphone input** - Browser-based audio recording in chat
- **Bilingual UI** - Full Arabic (RTL) / English (LTR) switching with 80+ i18n keys

### User Experience
- **JWT authentication** - Register/login with secure token-based auth
- **Dark/light theme** - Full theme toggle with persistence
- **Mobile responsive** - Hamburger menu, responsive grids
- **Runtime configuration** - Switch LLM/embedding providers via UI without restart
- **Telegram bot** - Optional bot integration for queries via Telegram

---

## System Architecture

```mermaid
graph TD
    subgraph Frontend ["User Interfaces"]
        UI[Web Dashboard]
        TG[Telegram Bot]
    end

    subgraph Backend ["FastAPI Application Layer"]
        API[API Routes]
        Auth[JWT Auth]

        subgraph Services ["Core Services"]
            Loader[Document Loader]
            Chunker[Text Splitter]
            Embedder[Embedding Service]
            Retriever[Query Service]
            GenAI[LLM Answer Service]
            Interview[Interview Service]
            SRS[SRS Service]
            STT[STT Service]
        end
    end

    subgraph Data ["Persistence Layer"]
        PG[(PostgreSQL + pgvector)]
        FS[File Storage]
        Qdrant[(Qdrant Vector DB)]
    end

    UI -->|HTTP/REST| API
    TG -->|Webhook| API

    API --> Auth
    Auth --> Services

    Loader -->|Raw Text| Chunker
    Chunker -->|Chunks| Embedder
    Embedder -->|Vectors| PG
    Embedder -->|Vectors| Qdrant

    Retriever <-->|Semantic Search| PG
    Retriever <-->|Semantic Search| Qdrant

    GenAI <-->|Inference| Gemini[Google Gemini API]
    STT <-->|Whisper| Groq[Groq API]
```

---

## Technical Pipeline

### Phase 1: Ingestion & Chunking
1. **File Upload** - Supports PDF, DOCX, TXT. Validated for MIME type and size.
2. **Text Extraction** - Content stripped of non-printable characters.
3. **Parent-Child Chunking** -
   - Parent chunks: `3000` chars with `600` overlap
   - Child chunks: `1000` chars with `200` overlap
   - Strategy configurable via `CHUNK_STRATEGY` env var

### Phase 2: Vectorization
- **Providers**: Gemini (`gemini-embedding-001`), Cohere (`embed-multilingual-v3.0`), Voyage AI (`voyage-3-large`), BGE-M3
- **Batching**: Configurable batch size and concurrency for rate limit compliance
- **Storage**: pgvector (PostgreSQL extension) or Qdrant

### Phase 3: Retrieval & Generation
1. **Query Embedding** - Same embedding model as indexing
2. **Similarity Search** - Cosine similarity, configurable top-K (default: 5, max: 20)
3. **Optional Hybrid Search** - Dense + sparse retrieval with configurable alpha
4. **Optional Reranking** - Post-retrieval reranking for precision
5. **Streaming Generation** - Gemini / OpenRouter / Groq / Cerebras via SSE

### Phase 4: Interview & SRS (AI Business Analyst)
1. **Interview Mode** - Guided 5-stage conversation with the client
2. **Live Document** - Real-time summary of gathered requirements
3. **SRS Generation** - Structured document from conversation history
4. **Review & Edit** - Inline editing of SRS sections
5. **Handoff** - Package and deliver to engineering team

---

## Tech Stack

| Component | Technology | Description |
|-----------|------------|-------------|
| **Backend** | **FastAPI** | High-performance async Python framework |
| **LLM Providers** | **Gemini, OpenRouter, Groq, Cerebras** | Factory pattern - switchable at runtime |
| **Embeddings** | **Gemini, Cohere, Voyage AI, BGE-M3** | Multi-provider with batch processing |
| **Vector DB** | **pgvector / Qdrant** | Configurable vector storage |
| **ORM** | **SQLAlchemy (async)** | Async database with 6 models |
| **Auth** | **PyJWT + bcrypt** | JWT token authentication |
| **STT** | **Groq Whisper** | Speech-to-text for 18 languages |
| **PDF Export** | **fpdf2** | SRS document export |
| **Frontend** | **Vanilla JS/CSS** | Lightweight, no build step |

---

## Installation & Setup

### Prerequisites
- Python 3.8+
- [uv](https://docs.astral.sh/uv/) (fast Python package installer)
- Docker Desktop (recommended for PostgreSQL + Qdrant)
- Google Gemini API Key

### Quick Start (Windows)

1. **Clone & Setup**:
   ```powershell
   git clone https://github.com/ZozElwakil/RAGMind---EELU-Project.git
   cd RAGMind---EELU-Project
   .\setup.bat
   ```
   This script creates the virtual environment, installs requirements, sets up `.env`, starts Docker containers, and initializes the database.

2. **Configure Environment**:
   Open `.env` and set the required keys:
   ```env
   # Required
   GEMINI_API_KEY=AIzaSy...
   DATABASE_URL=postgresql+asyncpg://ragmind:ragmind123@localhost:5555/ragmind

   # Authentication (change in production!)
   JWT_SECRET=your-secure-secret-here

   # Optional - Speech-to-Text
   GROQ_API_KEY=gsk_...

   # Optional - Alternative embedding providers
   COHERE_API_KEY=...
   VOYAGE_API_KEY=...
   ```

3. **Start Docker Services**:
   ```powershell
   .\start_docker.bat
   ```

4. **Run the Application**:
   ```powershell
   .\start_backend.bat
   ```

5. Visit **http://localhost:8000** - Register an account and start using RAGMind.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://ragmind:ragmind123@localhost:5555/ragmind` | PostgreSQL connection string |
| `GEMINI_API_KEY` | Yes | - | Google Gemini API key |
| `JWT_SECRET` | Yes (prod) | `ragmind-secret-change-me-in-production` | Secret for JWT token signing |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `JWT_EXPIRY_HOURS` | No | `72` | Token expiry in hours |
| `LLM_PROVIDER` | No | `gemini` | LLM provider selection |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Gemini model name |
| `EMBEDDING_PROVIDER` | No | `gemini` | Embedding provider (gemini/cohere/voyage/hf) |
| `VECTOR_DB_PROVIDER` | No | `pgvector` | Vector DB (pgvector/qdrant) |
| `GROQ_API_KEY` | No | - | Groq API key for STT (Whisper) |
| `COHERE_API_KEY` | No | - | Cohere API key for embeddings |
| `VOYAGE_API_KEY` | No | - | Voyage AI API key for embeddings |
| `CHUNK_SIZE` | No | `1000` | Text chunk size |
| `CHUNK_OVERLAP` | No | `200` | Chunk overlap |
| `CHUNK_STRATEGY` | No | `parent_child` | Chunking strategy |
| `RETRIEVAL_TOP_K` | No | `5` | Number of results to retrieve |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `TELEGRAM_BOT_TOKEN` | No | - | Telegram bot token |

See `.env.example` for the full list with descriptions.

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user (name, email, password) |
| POST | `/auth/login` | Login and receive JWT token |
| GET | `/auth/me` | Get current user info (requires Bearer token) |

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/projects` | List all projects |
| POST | `/projects` | Create new project |
| GET | `/projects/{id}` | Get project details |
| PUT | `/projects/{id}` | Update project |
| DELETE | `/projects/{id}` | Delete project |

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/projects/{id}/documents` | Upload document |
| GET | `/projects/{id}/documents` | List project documents |
| POST | `/documents/{id}/process` | Process (chunk + embed) document |
| DELETE | `/documents/{id}` | Delete document |

### Query & Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/query` | RAG query with streaming response (SSE) |
| GET | `/projects/{id}/messages` | Get chat history |
| DELETE | `/projects/{id}/messages` | Clear chat history |

### Interview & SRS
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/interview/respond` | Send message in interview mode |
| POST | `/projects/{id}/srs/generate` | Generate SRS from conversation |
| GET | `/projects/{id}/srs/latest` | Get latest SRS draft |
| GET | `/projects/{id}/srs/{srs_id}/pdf` | Export SRS as PDF |

### Speech-to-Text
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/stt/transcribe` | Transcribe audio file (supports 18 languages) |

### Handoff
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/projects/{id}/handoff` | Create project handoff package |

### Configuration
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/config` | Get current runtime configuration |
| PUT | `/config` | Update runtime configuration |
| GET | `/health` | Health check |
| GET | `/stats` | System statistics |

---

## Project Structure

```
RAGMind/
├── backend/
│   ├── config.py                # Pydantic settings (env vars)
│   ├── main.py                  # FastAPI app entry point
│   ├── database/
│   │   ├── __init__.py          # DB engine & session
│   │   └── models.py            # SQLAlchemy models (Project, Asset, Chunk, ChatMessage, SRSDraft, User)
│   ├── routes/
│   │   ├── auth.py              # JWT authentication (register/login/me)
│   │   ├── projects.py          # Project CRUD
│   │   ├── documents.py         # Document upload & processing
│   │   ├── query.py             # RAG query with SSE streaming
│   │   ├── messages.py          # Chat message history
│   │   ├── interview.py         # Guided interview mode
│   │   ├── srs.py               # SRS generation & PDF export
│   │   ├── stt.py               # Speech-to-text transcription
│   │   ├── handoff.py           # Project handoff to engineering
│   │   ├── health.py            # Health check
│   │   ├── stats.py             # System statistics
│   │   ├── bot_config.py        # Telegram bot configuration
│   │   └── app_config.py        # Runtime AI/RAG configuration
│   ├── services/
│   │   ├── interview_service.py # Interview stage management
│   │   ├── srs_service.py       # SRS generation logic
│   │   └── stt_service.py       # Audio transcription via Groq
│   └── providers/               # LLM, Embedding, VectorDB factories
├── frontend/
│   ├── index.html               # Single-page application
│   ├── app.js                   # Application logic (views, state, API)
│   └── style.css                # Styles (dark/light theme, RTL/LTR)
├── telegram_bot/                # Telegram bot integration
├── uploads/                     # Document storage
├── docker-compose.yml           # PostgreSQL + pgvector + Qdrant
├── setup.bat                    # Full project setup script
├── start.bat                    # Start all services
├── start_backend.bat            # Start backend only
├── start_docker.bat             # Start Docker containers
└── .env.example                 # Environment variables template
```

---

## Database Models

| Model | Table | Description |
|-------|-------|-------------|
| **User** | `users` | User accounts (name, email, password_hash, role) |
| **Project** | `projects` | Projects with name, description, language |
| **Asset** | `assets` | Uploaded documents linked to projects |
| **Chunk** | `chunks` | Text chunks with embeddings (pgvector) |
| **ChatMessage** | `chat_messages` | Conversation history per project |
| **SRSDraft** | `srs_drafts` | Generated SRS documents with versions |

---

## Usage Workflow

### 1. Register & Login
Create an account at the login screen. The JWT token is stored in localStorage.

### 2. Create a Project
Click "New Project" and provide a name, description, and language (Arabic/English).

### 3. Upload Documents
Drag-and-drop or click to upload PDF/DOCX/TXT files. Click "Process" to run the ingestion pipeline.

### 4. Ask Questions (RAG Mode)
Use the chat interface to ask questions about your documents. Answers stream in real-time with source citations.

### 5. Interview Mode (AI Business Analyst)
Toggle "Interview Mode" to start a guided requirements gathering session:
- **Discovery** - Understanding the business problem
- **Scope** - Defining project boundaries
- **Users** - Identifying target users and personas
- **Features** - Listing required features
- **Constraints** - Technical and business constraints

The split-screen co-pilot panel shows a live summary of gathered requirements.

### 6. Generate SRS
Navigate to the SRS tab to generate a structured Software Requirements Specification from your interview conversation. Edit sections inline and export to PDF.

### 7. Handoff
After confirming the SRS, hand off the project package (SRS + conversation summary + client info) to the engineering team.

---

## Contributors

- **Abdulmoezz Elwakil** ([@ZozElwakil](https://github.com/ZozElwakil)) - Core Logic & Architecture

## License
This project is licensed under the **MIT License**.
