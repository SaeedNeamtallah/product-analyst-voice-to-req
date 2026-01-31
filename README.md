# 🧠 RAGMind - Intelligent Document Intelligence Platform

![Project Status](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.68%2B-green)
![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-orange)
![License](https://img.shields.io/badge/License-MIT-purple)

**RAGMind** is an enterprise-grade Retrieval-Augmented Generation (RAG) system designed to transform static documents into interactive knowledge bases. By leveraging **Google's Gemini 2.5 Flash** for reasoning and **pgvector/Qdrant** for semantic search, it offers a high-precision, low-latency solution for specific domain knowledge extraction.

Built for the **EELU University Project**, this system bridges the gap between raw data and actionable intelligence.

---

## 🚀 Key Use Cases

### 1. 🎓 Academic & Research Assistant
Ideal for students and researchers handling massive volumes of papers and textbooks.
*   **Scenario**: A student uploads 10 PDF textbooks and 20 lecture slides.
*   **Action**: "Provide a comparative summary of 'Neural Networks' vs 'Decision Trees' based on Chapters 4 and 5."
*   **Outcome**: The system retrieves specific paragraphs from both chapters and synthesizes a coherent comparison with citations.

```mermaid
graph LR
    A[Student] -->|Uploads Thesis/Notes| B(Document Ingestion)
    B --> C{Knowledge Base}
    A -->|Ask: 'Explain Quantum Entanglement'| D[RAG Engine]
    C --> D
    D -->|Synthesized Answer| A
```

### 2. ⚖️ Legal Contract Analysis
For legal professionals reviewing complex agreements.
*   **Scenario**: Uploading a 50-page Service Level Agreement (SLA).
*   **Action**: "What are the termination clauses and penalties for early exit?"
*   **Outcome**: Extracts exact clauses, references page numbers, and summarizes the risk factors.

### 3. 🏢 Corporate Knowledge Hub
For HR and IT departments to automate internal support.
*   **Scenario**: Storing company policies, insurance documents, and IT troubleshooting guides.
*   **Action**: Employee asks "How do I claim dental insurance?" via Telegram Bot.
*   **Outcome**: Instant instructions with links to the relevant forms found in the "Employee Handbook 2024".

---

## 🛠️ System Architecture

RAGMind follows a modern, decoupled microservices-ready architecture using the **Factory Pattern** for provider flexibility.

```mermaid
graph TD
    subgraph Frontend ["User Interfaces"]
        UI[Web Dashboard]
        TG[Telegram Bot]
    end

    subgraph Backend ["FastAPI Application Layer"]
        API[API Routes]
        Auth[Auth Middleware]
        
        subgraph Services ["Core Services"]
            Loader[Document Loader]
            Chunker[Text Splitter]
            Embedder[Embedding Service]
            Retriever[Query Service]
            GenAI[LLM Answer Service]
        end
    end

    subgraph Data ["Persistence Layer"]
        PG[(PostgreSQL + pgvector)]
        FS[File Storage]
        Qdrant[(Qdrant Vector DB)]
    end

    UI -->|HTTP/REST| API
    TG -->|Webhook| API
    
    API --> Services
    
    Loader -->|Raw Text| Chunker
    Chunker -->|Chunks| Embedder
    Embedder -->|Vectors| PG
    Embedder -->|Vectors| Qdrant
    
    Retriever <-->|Semantic Search| PG
    Retriever <-->|Semantic Search| Qdrant
    
    GenAI <-->|Inference| Gemini[Google Gemini API]
```

---

## ⚙️ The Technical Pipeline (Deep Dive)

The system processes data through a strict **ETL (Extract, Transform, Load)** pipeline optimized for RAG.

### Phase 1: Ingestion & Chunking
1.  **File Upload**: Supports PDF, DOCX, TXT. Files are validated for MIME type and size.
2.  **Text Extraction**: content is stripped of non-printable characters.
3.  **Recursive Chunking**:
    *   Strategy: `RecursiveCharacterTextSplitter`
    *   Configuration: `chunk_size=1000`, `chunk_overlap=200`
    *   **Why?**: This preserves semantic context by keeping paragraphs together while ensuring chunks fit within the embedding model's context window.

### Phase 2: Vectorization (Embedding)
1.  **Model**: `models/gemini-embedding-001` (Google).
2.  **Dimension**: 768-dimensional dense vectors.
3.  **Batching**: Chunks are processed in batches (default: 10) to respect API rate limits.

### Phase 3: Retrieval & Generation (The "RAG" Loop)
1.  **Query Embedding**: User query is converted to a vector using the same model.
2.  **Similarity Search**:
    *   Metric: Cosine Similarity (via `pgvector` or `Qdrant`).
    *   Top-K: Retrieves the top 5 most relevant distinct chunks.
3.  **Prompt Engineering**:
    *   System constructs a prompt containing: "Context: [Retrieved Chunks] + Question: [User Query]".
    *   Instruction: "Answer based ONLY on the context provided."
4.  **Generation**:
    *   Model: `Gemini 2.5 Flash` (or configured model).
    *   Output: Streaming text response.

#### Query Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User
    participant API as FASTAPI
    participant V as VectorDB
    participant L as LLM (Gemini)
    
    U->>API: POST /query "Summarize the intro"
    
    Note over API: 1. Generate Query Embedding
    API->>L: Embed("Summarize the intro")
    L-->>API: Vector[0.12, -0.4, ...]
    
    Note over API: 2. Semantic Search
    API->>V: Search(Vector, Limit=5)
    V-->>API: Returns [Chunk A, Chunk B, Chunk C]
    
    Note over API: 3. Construct Context Prompt
    API->>L: Generate(Context + Question)
    L-->>API: "The introduction covers..."
    
    API->>U: Final Answer
```

---

## 💻 Tech Stack

| Component | Technology | Description |
|-----------|------------|-------------|
| **Backend Framework** | **FastAPI** | High-performance async Python framework. |
| **LLM Provider** | **Google Gemini** | Using `gemini-2.0-flash` (configurable) for reasoning. |
| **Embeddings** | **Titan/Gemini** | `gemini-embedding-001` for vector representation. |
| **Vector Database** | **PostgreSQL (pgvector)** | Relational + Vector data in one place. Optional Qdrant support. |
| **ORM** | **SQLAlchemy** | Async ORM for database interactions. |
| **Task Queue** | **AsyncIO** | Python's native async/await for non-blocking operations. |
| **Frontend** | **Vanilla JS/CSS** | Lightweight, clean UI without complex build steps. |

---

## 📦 Installation & Setup

### Prerequisites
*   Python 3.8+
*   PostgreSQL 14+ (with `vector` extension installed)
*   A Google Cloud API Key (for Gemini)

### Quick Start (Windows)
The project includes automated scripts for instant setup.

1.  **Clone & Setup**:
    ```powershell
    git clone https://github.com/ZozElwakil/RAGMind---EELU-Project.git
    cd RAGMind---EELU-Project
    .\setup.bat
    ```
    *This script creates the virtual environment, installs requirements, and sets up the .env file.*

2.  **Environment Config**:
    Open `.env` and paste your keys:
    ```env
    DATABASE_URL=postgresql+asyncpg://postgres:password@localhost/ragmind
    GEMINI_API_KEY=AIzaSy...
    ```

3.  **Initialize DB**:
    ```powershell
    python -m backend.init_database
    ```

4.  **Run**:
    ```powershell
    .\start_backend.bat
    ```

Visit **http://localhost:8000** to use the application.

---

## 📂 Project Structure

```bash
RAGMind/
├── backend/
│   ├── services/          # Business logic (RAG, Chunking, Parsing)
│   ├── providers/         # Interfaces for LLMs and VectorDBs
│   ├── routes/            # API Endpoints
│   ├── database/          # SQLAlchemy models and connection
│   └── main.py            # App entry point
├── frontend/              # Web UI (HTML/JS/CSS)
├── telegram_bot/          # Telegram Bot integration code
├── uploads/               # Temporary storage for documents
└── scripts/               # .bat helper scripts
```

---

## 👥 Contributors

*   **Abdulmoezz Elwakil** ([@ZozElwakil](https://github.com/ZozElwakil)) - Core Logic & Architecture

## 📄 License
This project is licensed under the **MIT License**.
