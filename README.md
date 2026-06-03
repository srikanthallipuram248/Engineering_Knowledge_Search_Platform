# Engineering Knowledge Search Platform

An internal AI-powered knowledge assistant that lets teams **analyze code repositories** and **chat with their documentation and codebase** using a RAG (Retrieval-Augmented Generation) pipeline.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Agent Phases](#agent-phases)
- [Data Ingestion Strategy](#data-ingestion-strategy)
- [Code Repository Ingestion](#code-repository-ingestion)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Development Guide](#development-guide)

---

## Overview

The platform has two core capabilities:

| Phase | Name | What it does |
|-------|------|-------------|
| **Phase 1** | Repo Analyzer Agent | Accepts a code repository (zip or Git URL), reads its README or folder structure, and produces a high-level architecture and project summary using an LLM |
| **Phase 2** | Knowledge Chat Agent | RAG-powered chatbot that answers questions about policies, code conventions, architecture decisions, and improvement areas from ingested documents and code |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Browser / Client                        │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTP
┌───────────────────────────────▼─────────────────────────────────┐
│                    Backend  (FastAPI · port 5000)                │
│   Auth · Project Management · File Upload Gateway               │
└───────────────────────────────┬─────────────────────────────────┘
                                │ Internal HTTP
┌───────────────────────────────▼─────────────────────────────────┐
│                  AI Pipeline  (FastAPI · port 8000)              │
│                                                                  │
│  ┌──────────────────┐        ┌──────────────────────────────┐   │
│  │  Repo Analyzer   │        │       Chat / RAG Agent        │   │
│  │     Agent        │        │                               │   │
│  │  (Phase 1)       │        │  Retriever → Reranker →       │   │
│  └────────┬─────────┘        │  Context Builder → LLM        │   │
│           │                  └──────────────┬───────────────┘   │
│           │                                 │                    │
│  ┌────────▼─────────────────────────────────▼───────────────┐   │
│  │                   Ingestion Pipeline                       │   │
│  │  Loaders → Parsers → Chunkers → Embedder → Vector Store   │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Vector Store (ChromaDB)  ·  LLM (Claude)  ·  Embeddings        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
Engineering_Knowledge_Search_Platform/
│
├── Backend/                          # REST gateway — auth, projects, file uploads
│   ├── app/
│   │   ├── main.py                   # FastAPI app factory + middleware
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic-Settings environment config
│   │   │   ├── security.py           # JWT creation / verification
│   │   │   ├── exceptions.py         # Custom HTTP exception classes
│   │   │   └── logging.py            # Structured JSON logging setup
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── router.py         # Aggregates all v1 routers
│   │   │       ├── endpoints/
│   │   │       │   ├── health.py     # GET /health
│   │   │       │   ├── auth.py       # POST /auth/register, /auth/login
│   │   │       │   └── projects.py   # CRUD for projects/workspaces
│   │   │       └── schemas/
│   │   │           ├── auth.py       # LoginRequest, TokenResponse …
│   │   │           └── projects.py   # ProjectCreate, ProjectResponse …
│   │   ├── models/
│   │   │   ├── base.py               # SQLAlchemy declarative base
│   │   │   ├── user.py               # User ORM model
│   │   │   └── project.py            # Project ORM model
│   │   ├── database/
│   │   │   └── session.py            # AsyncSession factory + get_db dep
│   │   ├── services/
│   │   │   ├── auth_service.py       # Register, login, token logic
│   │   │   └── project_service.py    # Project CRUD business logic
│   │   └── utils/
│   │       └── file_utils.py         # Safe filename, MIME validation
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
│
├── AI_pipeline/                      # AI brain — ingestion, analysis, RAG
│   ├── app/
│   │   ├── main.py                   # FastAPI app factory + lifespan
│   │   ├── core/
│   │   │   ├── config.py             # All AI/LLM/vector-store settings
│   │   │   ├── exceptions.py         # IngestionError, EmbeddingError …
│   │   │   └── logging.py            # Structured logging
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── router.py
│   │   │       ├── endpoints/
│   │   │       │   ├── health.py
│   │   │       │   ├── repo_analyzer.py  # POST /analyze/repo
│   │   │       │   ├── ingestion.py      # POST /ingest (files, zip, git)
│   │   │       │   └── chat.py           # POST /chat
│   │   │       └── schemas/
│   │   │           ├── repo_analyzer.py  # RepoAnalyzeRequest/Response
│   │   │           ├── ingestion.py      # IngestRequest/Response
│   │   │           └── chat.py           # ChatRequest/Response
│   │   │
│   │   ├── agents/                   # High-level orchestrators (Phase 1 & 2)
│   │   │   ├── base.py               # IAgent abstract base class
│   │   │   ├── repo_analyzer_agent.py  # Phase 1: repo → summary
│   │   │   └── chat_agent.py           # Phase 2: question → RAG answer
│   │   │
│   │   ├── ingestion/                # Pluggable data ingestion subsystem
│   │   │   ├── pipeline.py           # Orchestrates loader→parser→chunker→embed→store
│   │   │   ├── loaders/              # How to *get* the raw content
│   │   │   │   ├── base.py           # ILoader interface
│   │   │   │   ├── file_loader.py    # Single file from disk/upload
│   │   │   │   ├── zip_loader.py     # Extract + walk a .zip archive
│   │   │   │   └── git_loader.py     # Clone a git URL then walk tree
│   │   │   └── parsers/              # How to *read* each file type
│   │   │       ├── base.py           # IParser interface
│   │   │       ├── pdf_parser.py     # PyMuPDF / pdfplumber
│   │   │       ├── text_parser.py    # .txt, .md, .rst, .csv
│   │   │       └── code_parser.py    # AST / tree-sitter function-level parsing
│   │   │
│   │   ├── chunking/                 # Split documents into indexable units
│   │   │   ├── base.py               # IChunker interface
│   │   │   ├── text_chunker.py       # Recursive token/semantic splitting
│   │   │   └── code_chunker.py       # Function / class level splitting
│   │   │
│   │   ├── embeddings/               # Convert chunks to vectors
│   │   │   ├── base.py               # IEmbedder interface
│   │   │   └── openai_embedder.py    # text-embedding-3-small / large
│   │   │
│   │   ├── vectorstore/              # Persist and query vectors
│   │   │   ├── base.py               # IVectorStore interface
│   │   │   └── chroma_store.py       # ChromaDB implementation
│   │   │
│   │   ├── rag/                      # Retrieval-Augmented Generation
│   │   │   ├── retriever.py          # Similarity search + metadata filter
│   │   │   ├── reranker.py           # Cross-encoder / score re-ranking
│   │   │   └── context_builder.py    # Assemble retrieved chunks → prompt context
│   │   │
│   │   ├── llm/                      # LLM abstraction layer
│   │   │   ├── base.py               # ILLM interface
│   │   │   ├── claude_client.py      # Anthropic Claude client (streaming)
│   │   │   └── prompts/
│   │   │       ├── repo_analyzer_prompts.py  # System + user prompts for Phase 1
│   │   │       └── chat_prompts.py           # System + user prompts for Phase 2
│   │   │
│   │   └── services/                 # Use-case orchestration (called by endpoints)
│   │       ├── repo_analysis_service.py  # Drives the Repo Analyzer Agent
│   │       └── chat_service.py           # Drives the Chat Agent
│   │
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
│
├── Frontend/                         # React + Vite UI
│   └── src/
│       ├── components/
│       │   ├── common/               # Shared UI components
│       │   └── dashboard/            # Dashboard-specific components
│       ├── pages/                    # Route-level page components
│       ├── services/                 # Axios API clients
│       ├── auth/                     # Auth context + guards
│       ├── routes/                   # React Router config
│       ├── styles/                   # Global CSS / Tailwind config
│       └── utils/                    # Shared helpers
│
├── docker-compose.yml                # Orchestrates all three services
└── AGENTS.md                         # Agent design, prompts, and extension guide
```

---

## Agent Phases

### Phase 1 — Repo Analyzer Agent

**Input:** A code repository (uploaded `.zip` or a Git clone URL)

**Flow:**
```
Upload / Clone
     │
     ▼
Walk Directory Tree
     │
     ├──► README.md found?
     │         │ YES → Extract README text
     │         │ NO  → Build folder-tree snapshot (depth-limited)
     │
     ▼
LLM Prompt (Claude)
  • Project purpose and goals
  • Tech stack detected
  • High-level architecture
  • Key modules and their responsibilities
  • Suggested entry points for developers
     │
     ▼
Structured JSON Response
```

**No README heuristics** — when no README is found, the pipeline reads:
- Top-level `*.py` / `*.ts` / `*.go` files for imports and class/function names
- `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod` for dependency hints
- Directory names as architecture signal (e.g., `controllers/`, `services/`, `migrations/`)

---

### Phase 2 — Knowledge Chat Agent (RAG)

**Input:** A natural language question from the user

**Flow:**
```
User Question
     │
     ▼
Query Embedding (OpenAI)
     │
     ▼
Vector Store Retrieval (top-k chunks, metadata-filtered by project)
     │
     ▼
Reranker (cross-encoder score, optional)
     │
     ▼
Context Builder (assemble chunks → prompt window)
     │
     ▼
LLM Prompt (Claude) with injected context
     │
     ▼
Streamed Answer + Source Citations
```

---

## Data Ingestion Strategy

| Source Type | Loader | Parser | Chunker |
|-------------|--------|--------|---------|
| `.txt`, `.md`, `.rst` | `FileLoader` | `TextParser` | `TextChunker` (recursive, 512 tok, 50 overlap) |
| `.pdf` | `FileLoader` | `PdfParser` (PyMuPDF) | `TextChunker` |
| `.csv` | `FileLoader` | `TextParser` | Row-level chunking |
| `.zip` of a project | `ZipLoader` | dispatched by extension | `TextChunker` or `CodeChunker` |
| Git repository URL | `GitLoader` (GitPython) | dispatched by extension | `CodeChunker` |

Each chunk is stored with rich metadata:
```json
{
  "project_id": "uuid",
  "source_type": "pdf | text | code",
  "file_path": "docs/leave_policy.pdf",
  "language": "python",
  "symbol": "UserAuthService.login",
  "page": 3,
  "chunk_index": 12
}
```

---

## Code Repository Ingestion

Code repos require special treatment — splitting by lines loses semantic context. The platform uses **AST-level chunking**:

### How it works

```
Git Clone / Zip Extract
         │
         ▼
  Filter relevant files
  (skip: .git, node_modules, __pycache__, *.lock, binaries)
         │
         ▼
  Language detection (by extension)
         │
         ▼
  AST parsing per language        ◄── code_parser.py
  • Python  → ast module
  • JS/TS   → tree-sitter
  • Go/Java → tree-sitter
         │
         ▼
  Extract semantic units:
  • Each top-level function   → 1 chunk
  • Each class + its methods  → 1 chunk
  • Module-level docstring    → 1 chunk
  • Long functions split at   → logical block boundaries
         │
         ▼
  Chunk metadata:
  { file, function_name, class_name, language, start_line, end_line }
         │
         ▼
  Embed + store in vector DB
```

### Why AST-level chunking matters for code Q&A

| Approach | Problem |
|----------|---------|
| Line-based (512 chars) | Splits functions mid-way; context is broken |
| File-level | Too large for embedding window; noisy retrieval |
| **AST / function-level** | Preserves full semantic unit; clean retrieval |

### Supported languages (code_parser.py)

- Python (stdlib `ast`)
- JavaScript / TypeScript (`tree-sitter-javascript`, `tree-sitter-typescript`)
- Java, Go, Rust (tree-sitter grammars — plug-in ready)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI, SQLAlchemy, Alembic, PostgreSQL |
| AI Pipeline | FastAPI, LangChain (optional), Anthropic Claude |
| Embeddings | OpenAI `text-embedding-3-small` |
| Vector Store | ChromaDB (dev) / Pinecone or pgvector (prod) |
| Code Parsing | Python `ast`, `tree-sitter` |
| PDF Parsing | PyMuPDF (`fitz`) |
| Git Cloning | GitPython |
| Auth | JWT (python-jose) + bcrypt |
| Frontend | React 18, Vite, Tailwind CSS |
| Containerisation | Docker, Docker Compose |

---

## Getting Started

### Prerequisites

- Docker Desktop
- Git

### Run with Docker Compose

```bash
git clone <repo-url>
cd Engineering_Knowledge_Search_Platform

# Copy and fill in env files
cp Backend/.env.example Backend/.env
cp AI_pipeline/.env.example AI_pipeline/.env

docker compose up --build
```

### Service URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:5000 |
| AI Pipeline | http://localhost:8000 |
| API Docs (Backend) | http://localhost:5000/docs |
| API Docs (AI Pipeline) | http://localhost:8000/docs |

---

## Environment Variables

### Backend `.env`

```env
APP_NAME=Engineering Knowledge Search Platform
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql+asyncpg://user:password@db:5432/eksp
CORS_ORIGINS=["http://localhost:3000"]
AI_PIPELINE_URL=http://ai-pipeline:8000
```

### AI Pipeline `.env`

```env
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-6
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small
CHROMA_PERSIST_DIR=./data/chroma
UPLOAD_DIR=./data/uploads
MAX_UPLOAD_SIZE_MB=100
```

---

## API Reference

### AI Pipeline — Phase 1

```
POST /api/v1/analyze/repo
Content-Type: multipart/form-data

Body:
  file: <zip file>         (optional — mutually exclusive with git_url)
  git_url: <string>        (optional — public repo URL)
  project_id: <uuid>
```

```json
// Response
{
  "project_id": "uuid",
  "summary": "This is a FastAPI backend for ...",
  "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
  "architecture": "Layered MVC with ...",
  "key_modules": [
    { "name": "services/", "role": "Business logic layer" }
  ],
  "readme_found": true
}
```

### AI Pipeline — Phase 2

```
POST /api/v1/chat
Content-Type: application/json

{
  "project_id": "uuid",
  "message": "What is our leave policy?",
  "chat_history": []
}
```

```json
// Response (streaming SSE)
{
  "answer": "Based on the HR policy document ...",
  "sources": [
    { "file": "docs/hr_policy.pdf", "page": 4, "score": 0.91 }
  ]
}
```

### AI Pipeline — Ingestion

```
POST /api/v1/ingest
Content-Type: multipart/form-data

Body:
  project_id: <uuid>
  source_type: "file" | "zip" | "git"
  files[]: <file uploads>       (for type=file or type=zip)
  git_url: <string>             (for type=git)
```

---

## Development Guide

### SOLID Principles Applied

| Principle | Where |
|-----------|-------|
| **S**ingle Responsibility | Each parser, chunker, embedder does exactly one job |
| **O**pen/Closed | Add a new parser by implementing `IParser` — no existing code changes |
| **L**iskov Substitution | `ChromaStore`, `PineconeStore` are interchangeable via `IVectorStore` |
| **I**nterface Segregation | `ILoader`, `IParser`, `IChunker`, `IEmbedder`, `IVectorStore` — thin, focused interfaces |
| **D**ependency Inversion | Services depend on interfaces, not concrete classes; injected via FastAPI `Depends` |

### Adding a new file type parser

1. Create `AI_pipeline/app/ingestion/parsers/my_format_parser.py`
2. Implement the `IParser` interface (`parse(path) -> List[Document]`)
3. Register it in `ingestion/pipeline.py`'s parser dispatch map

### Adding a new LLM provider

1. Create `AI_pipeline/app/llm/my_provider_client.py`
2. Implement the `ILLM` interface (`complete(prompt) -> str`, `stream(prompt) -> AsyncIterator`)
3. Swap the binding in `core/config.py`
