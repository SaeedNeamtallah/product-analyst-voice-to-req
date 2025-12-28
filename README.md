# RAGMind - Intelligent Document Q&A System

A robust Retrieval-Augmented Generation (RAG) system built with FastAPI that enables document upload, intelligent processing, vector-based similarity search, and AI-powered answer generation. Upload documents (PDF, TXT, DOCX), automatically process them into searchable chunks with embeddings, store in PostgreSQL with pgvector, and retrieve contextual answers powered by Google Gemini for your AI applications.

## 🏗️ Architecture Overview

### Core Components

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Web Client    │────▶│   FastAPI API   │────▶│   Controllers   │
│  (Upload/Query) │     │   Routes        │     │  (Business      │
│   + Telegram    │     │                 │     │   Logic)        │
└─────────────────┘     └─────────────────┘     └─────────┬───────┘
                                                           │
                        ┌──────────────────────────────────┼──────────────┐
                        ▼                                  ▼              ▼
                ┌───────────────┐              ┌──────────────┐  ┌──────────────┐
                │  PostgreSQL   │              │ LLM Provider │  │ Vector DB    │
                │  + pgvector   │              │ (Google      │  │ (pgvector/   │
                │  (Chunks,     │              │  Gemini      │  │  Qdrant)     │
                │   Projects,   │              │  2.5 Flash)  │  │              │
                │   Assets)     │              │              │  │              │
                └───────────────┘              └──────────────┘  └──────────────┘
                        ▲                              ▲                  ▲
                        │                              │                  │
                        └──────────┬───────────────────┴──────────────────┘
                                   ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │   LangChain     │────▶│   Document      │
                        │  Text Splitter  │     │   Loaders       │
                        │  (Chunking)     │     │  (PDF, TXT,     │
                        │                 │     │   DOCX)         │
                        └─────────────────┘     └─────────────────┘
                                   ▲
                                   │
                        ┌─────────────────┐
                        │   File Storage  │
                        │  (Project-based │
                        │   Organization) │
                        └─────────────────┘
```

### Data Flow

```
Document Upload → File validation → Unique naming → Project storage
                                                          ↓
Document Processing → Content extraction → Text chunking → Metadata preservation
                                                          ↓
Data Storage → PostgreSQL (via SQLAlchemy async) → Project organization
                                                          ↓
Vector Embeddings → Gemini Embeddings → Generate embeddings → Store in VectorDB
                                                          ↓
Similarity Search → Query vectors → VectorDB search → Retrieve top-k chunks
                                                          ↓
Answer Generation → Prompt construction → Gemini LLM → AI-powered answers
```

### Provider Architecture

The system uses a **Factory Pattern** for extensible provider management:

#### LLM Providers:
- Abstract `LLMInterface` defines the contract
- `LLMProviderFactory` creates provider instances
- Support for **Google Gemini** (easily extensible to OpenAI, Cohere, etc.)
- Unified API for text generation and embeddings

#### VectorDB Providers:
- Abstract `VectorDBInterface` defines the contract
- `VectorDBProviderFactory` creates provider instances
- **PGVector** implementation for PostgreSQL with pgvector extension
- **Qdrant** implementation for standalone vector storage
- Support for collection management and similarity search
- Configurable distance metrics (cosine, dot product, L2)

## 🛠️ Technical Stack

- **Backend Framework**: FastAPI with async/await patterns and lifespan context management
- **Database**: PostgreSQL with pgvector extension for vector similarity
- **ORM**: SQLAlchemy 2.0 with async support (asyncpg driver)
- **Vector Database**: PGVector (PostgreSQL) or Qdrant for vector storage
- **LLM Provider**: Google Gemini 2.5 Flash for embeddings and text generation
- **Document Processing**: LangChain (text splitting, document loading)
- **PDF Processing**: pypdf for efficient PDF text extraction
- **DOCX Processing**: python-docx for Word document parsing
- **Data Validation**: Pydantic v2 with custom validators
- **File Handling**: aiofiles for async I/O operations
- **Bot Integration**: python-telegram-bot for Telegram interface
- **Python Version**: 3.8+
- **Additional Libraries**: asyncpg, sqlalchemy, alembic, aiofiles, python-dotenv, python-multipart, qdrant-client, google-generativeai, langchain

## 📁 Project Structure

```
RAGMind/
├── backend/                          # Python Backend
│   ├── main.py                       # FastAPI application & lifespan
│   ├── config.py                     # Settings management (Pydantic)
│   ├── requirements.txt              # Python dependencies
│   │
│   ├── routes/                       # API Endpoints
│   │   ├── __init__.py
│   │   ├── health.py                 # Health check endpoints
│   │   ├── projects.py               # Project management
│   │   ├── documents.py              # Document upload/management
│   │   ├── query.py                  # RAG query endpoints
│   │   ├── stats.py                  # Statistics endpoints
│   │   └── bot_config.py             # Telegram bot configuration
│   │
│   ├── controllers/                  # Business Logic Layer
│   │   ├── __init__.py
│   │   ├── project_controller.py     # Project CRUD operations
│   │   ├── document_controller.py    # Document processing logic
│   │   └── query_controller.py       # RAG query logic
│   │
│   ├── services/                     # Core Services
│   │   ├── __init__.py
│   │   ├── document_loader.py        # Document parsing (PDF, TXT, DOCX)
│   │   ├── chunking_service.py       # Text chunking with LangChain
│   │   ├── embedding_service.py      # Generate embeddings
│   │   ├── query_service.py          # Vector similarity search
│   │   ├── answer_service.py         # LLM answer generation
│   │   └── file_service.py           # File upload/storage
│   │
│   ├── database/                     # Database Layer
│   │   ├── __init__.py
│   │   ├── models.py                 # SQLAlchemy ORM models
│   │   ├── connection.py             # Database connection management
│   │   └── init_database.py          # Database initialization
│   │
│   └── providers/                    # External Service Integrations
│       ├── llm/                      # LLM Provider Abstraction
│       │   ├── __init__.py
│       │   ├── interface.py          # LLM interface definition
│       │   ├── factory.py            # Provider factory
│       │   └── gemini_provider.py    # Google Gemini implementation
│       │
│       └── vectordb/                 # Vector DB Abstraction
│           ├── __init__.py
│           ├── interface.py          # VectorDB interface
│           ├── factory.py            # Provider factory
│           ├── pgvector_provider.py  # PostgreSQL pgvector
│           └── qdrant_provider.py    # Qdrant implementation
│
├── frontend/                         # Web Frontend
│   ├── index.html                    # Main HTML (Arabic/English RTL)
│   ├── style.css                     # Styling (dark/light themes)
│   └── app.js                        # Application logic (Vanilla JS)
│
├── telegram_bot/                     # Telegram Bot
│   ├── __init__.py
│   ├── bot.py                        # Bot initialization
│   ├── config.py                     # Bot configuration
│   └── handlers.py                   # Message/command handlers
│
├── uploads/                          # File Storage
│   └── {project_id}/                 # Project-specific directories
│
├── .env                              # Environment variables
├── .env.example                      # Environment template
├── setup.bat                         # Automated setup script
├── start_backend.bat                 # Start backend server
├── start_telegram_bot.bat            # Start Telegram bot
├── create_database.sql               # Database initialization
└── README.md                         # This file
```

## 🚀 API Endpoints

### Health & Stats

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | System health check and status |
| GET | `/stats/` | Get statistics (projects, documents, chunks) |

### Project Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/projects/` | List all projects |
| POST | `/projects/` | Create new project |
| GET | `/projects/{id}` | Get project details |
| DELETE | `/projects/{id}` | Delete project and all associated data |
| GET | `/projects/{id}/documents` | List project documents |

### Document Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/projects/{id}/documents` | Upload document to project |
| DELETE | `/documents/{id}` | Delete document |
| GET | `/documents/{id}/chunks` | Get document text chunks |

### RAG/Query Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/projects/{id}/query` | Query project documents with AI-powered answers |

### Bot Configuration

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/bot/config` | Get Telegram bot configuration |
| POST | `/bot/config` | Update bot active project |
| POST | `/bot/profile` | Update bot profile name |

### Response Structure

All endpoints return JSON responses with consistent structure:

```json
{
  "status": "success",
  "message": "Operation completed successfully",
  "data": {}
}
```

## 📋 Request/Response Examples

### 1. Create Project

```bash
curl -X POST "http://localhost:8000/projects/" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "AI Research Papers",
       "description": "Collection of AI and ML research papers"
     }'
```

**Response:**
```json
{
  "id": 1,
  "name": "AI Research Papers",
  "description": "Collection of AI and ML research papers",
  "created_at": "2025-12-28T10:00:00Z",
  "updated_at": null
}
```

### 2. Upload Document

```bash
curl -X POST "http://localhost:8000/projects/1/documents" \
     -F "file=@research_paper.pdf"
```

**Response:**
```json
{
  "id": 1,
  "project_id": 1,
  "filename": "abc123_research_paper.pdf",
  "original_filename": "research_paper.pdf",
  "file_size": 524288,
  "file_type": "pdf",
  "status": "uploaded",
  "created_at": "2025-12-28T10:05:00Z"
}
```

### 3. Query Documents (RAG)

```bash
curl -X POST "http://localhost:8000/projects/1/query" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What are the main findings of the research?",
       "language": "en",
       "top_k": 5
     }'
```

**Response:**
```json
{
  "answer": "Based on the research papers, the main findings include: 1) Transformer architectures significantly outperform traditional RNNs in NLP tasks...",
  "sources": [
    {
      "chunk_id": 42,
      "content": "Our experiments demonstrate that...",
      "document_name": "research_paper.pdf",
      "similarity": 0.89
    },
    {
      "chunk_id": 87,
      "content": "The results show significant improvements...",
      "document_name": "research_paper.pdf",
      "similarity": 0.85
    }
  ],
  "context_used": 5
}
```

### 4. Search Similar Documents

```bash
curl -X POST "http://localhost:8000/projects/1/query" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "transformer architecture",
       "language": "en",
       "top_k": 3
     }'
```

**Response:**
```json
{
  "answer": "Transformer architecture is a neural network design...",
  "sources": [
    {
      "chunk_id": 15,
      "content": "The Transformer architecture relies on self-attention mechanisms...",
      "document_name": "attention_is_all_you_need.pdf",
      "similarity": 0.92
    }
  ],
  "context_used": 3
}
```

## 🔧 Configuration

### RAG Workflow

The RAG system follows a complete pipeline:

1. **Upload Documents**: Upload PDF, TXT, or DOCX files to project-specific directories
2. **Process & Chunk**: Extract text and split into semantic chunks with configurable overlap
3. **Generate Embeddings**: Create vector embeddings using Google Gemini
4. **Store Vectors**: Index embeddings in vector database (PGVector or Qdrant)
5. **Query Processing**: Convert user queries into embeddings
6. **Retrieve Context**: Find top-k most relevant document chunks via vector similarity
7. **Generate Answers**: Use Gemini LLM to generate contextual answers

### Key Features

- ✅ **Multi-Provider Support**: Switch between PGVector and Qdrant for vector storage
- ✅ **Bilingual UI**: Arabic and English support with RTL/LTR layouts
- ✅ **Telegram Integration**: Query documents via Telegram bot
- ✅ **Async Processing**: Non-blocking I/O for efficient operations
- ✅ **Flexible Chunking**: Configurable chunk sizes and overlap
- ✅ **Project Isolation**: Separate vector collections per project
- ✅ **Dark/Light Themes**: Modern UI with theme switching
- ✅ **Real-time Processing**: Live status updates for document processing

### Environment Variables

Create a `.env` file in the project root (see `.env.example` for template):

```ini
# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/ragmind

# LLM Provider Configuration
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash

# Vector Database Configuration
VECTOR_DB_PROVIDER=pgvector  # or qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# Storage Configuration
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=50

# Text Chunking Configuration
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Telegram Bot Configuration (Optional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_ADMIN_ID=

# CORS Configuration
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

# Logging Configuration
LOG_LEVEL=INFO
```

## 📊 Database Schema

### PostgreSQL Tables (with pgvector extension)

#### `projects` Table

```sql
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX ix_projects_name ON projects(name);
```

#### `assets` Table

```sql
CREATE TABLE assets (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    original_filename VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    file_size INTEGER NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'uploaded',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX ix_assets_project_id ON assets(project_id);
CREATE INDEX ix_assets_status ON assets(status);
```

#### `chunks` Table

```sql
CREATE TABLE chunks (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    embedding JSONB,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ix_chunks_project_id ON chunks(project_id);
CREATE INDEX ix_chunks_asset_id ON chunks(asset_id);
```

### Schema Features

- ✅ **Foreign Keys**: Proper relationships with cascading deletes
- ✅ **JSONB**: Flexible metadata storage
- ✅ **Timestamps**: Automatic tracking of creation/update times
- ✅ **Indexes**: Optimized for common query patterns
- ✅ **Vector Support**: pgvector extension for similarity search

## 📋 Prerequisites & Installation

### Prerequisites

- Python 3.8+
- PostgreSQL 14+ with pgvector extension
- Google Gemini API Key
- (Optional) Qdrant for vector storage
- (Optional) Telegram Bot Token

### Quick Start (Automated)

1. **Clone the repository:**

```bash
git clone https://github.com/yourusername/RAGMind.git
cd RAGMind
```

2. **Run the automated setup script:**

```bash
setup.bat
```

The setup script will:
- ✅ Check Python installation
- ✅ Create virtual environment
- ✅ Install all dependencies
- ✅ Create `.env` file from template
- ✅ Create necessary directories
- ✅ Guide database setup

3. **Configure environment variables:**

Edit `.env` file and add:
- `DATABASE_URL`
- `GEMINI_API_KEY`
- (Optional) `TELEGRAM_BOT_TOKEN`

4. **Setup PostgreSQL:**

```sql
CREATE DATABASE ragmind;
\c ragmind
CREATE EXTENSION vector;
```

5. **Initialize database tables:**

```bash
python -m backend.init_database
```

6. **Start the application:**

```bash
start_backend.bat
```

7. **Access the application:**
- Web UI: http://localhost:8000
- API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Manual Installation

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Create .env file
cp .env.example .env
# Edit .env with your credentials

# 4. Setup PostgreSQL
# Create database and install pgvector extension

# 5. Initialize database
python -m backend.init_database

# 6. Run the application
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

## 🧪 Testing - Complete RAG Workflow

### Step-by-Step Testing

```bash
# 1. Create a project
curl -X POST "http://localhost:8000/projects/" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Test Project",
       "description": "Testing RAG workflow"
     }'

# 2. Upload a PDF document
curl -X POST "http://localhost:8000/projects/1/documents" \
     -F "file=@sample.pdf"

# 3. Wait for automatic processing (status will change to 'completed')
# Check document status:
curl "http://localhost:8000/projects/1/documents"

# 4. Query the documents
curl -X POST "http://localhost:8000/projects/1/query" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What is the main topic?",
       "language": "en",
       "top_k": 5
     }'

# 5. Verify data in PostgreSQL
psql -U postgres -d ragmind
# SELECT COUNT(*) FROM chunks WHERE project_id = 1;
# SELECT * FROM assets WHERE project_id = 1;
```

### Testing Telegram Bot

1. Start the bot:
```bash
start_telegram_bot.bat
```

2. Configure active project in web UI:
- Go to "Bot Settings"
- Select active project
- Save configuration

3. Chat with bot on Telegram:
```
/start
Ask any question about your documents
```

## 🔐 Security Considerations

- ✅ **API Keys**: Stored in `.env` file (gitignored)
- ✅ **CORS**: Configured for allowed origins only
- ✅ **File Validation**: Type and size checks on upload
- ✅ **Database**: Async connection pooling with SQLAlchemy
- ✅ **Error Handling**: Graceful error messages without sensitive data
- ✅ **SQL Injection**: Protected by SQLAlchemy ORM

## 🐛 Troubleshooting

### Common Issues

**Database Connection Error:**
```
✓ Ensure PostgreSQL is running
✓ Verify DATABASE_URL in .env
✓ Check pgvector extension is installed
```

**Gemini API Error:**
```
✓ Verify GEMINI_API_KEY is valid
✓ Check API quota/limits
✓ Ensure internet connection
```

**File Upload Fails:**
```
✓ Check upload directory has write permissions
✓ Verify file type is supported (PDF, TXT, DOCX)
✓ Ensure file size under MAX_FILE_SIZE_MB
```

**Vector Search Returns No Results:**
```
✓ Verify documents are processed (status='completed')
✓ Check embeddings are generated
✓ Confirm Vector DB connection
```

## 📝 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

## 👥 Contributors

**Abdulmoezz Elwakil** ([@AbdulmoezzElwakil](https://github.com/ZozElwakil))

---

**Built with ❤️ for EELU University Project**
