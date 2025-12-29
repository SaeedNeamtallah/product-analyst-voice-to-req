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
