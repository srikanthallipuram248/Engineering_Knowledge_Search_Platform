# Engineering Knowledge Search Platform

An internal AI-powered knowledge assistant that lets engineering teams **analyze code repositories** and **chat with their documentation and codebase** using a Hybrid RAG pipeline.

---

## Table of Contents

- [Architecture](#architecture)
- [Hybrid RAG Decision Logic](#hybrid-rag-decision-logic)
- [Project Structure](#project-structure)
- [Agent Phases](#agent-phases)
- [Data Ingestion Strategy](#data-ingestion-strategy)
- [Code Repository Ingestion](#code-repository-ingestion)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│   Search UI │ Chat UI │ Document Viewer │ Admin Portal      │
└─────────────────────────┬──────────────────────────────────┘
                          │ HTTP
┌─────────────────────────▼──────────────────────────────────┐
│                     API GATEWAY                             │
│         Auth · Rate Limiting · Request Routing              │
└──────────┬──────────────────────────────┬───────────────────┘
           │                              │
    ┌──────▼──────┐                ┌──────▼──────┐
    │Search Service│               │ Chat Service │
    └──────┬──────┘                └──────┬──────┘
           │                              │
           └──────────────┬───────────────┘
                          ▼
              ┌───────────────────────┐
              │    Retrieval Layer    │
              └───────────┬───────────┘
                          ▼
              ┌───────────────────────┐
              │   Vector DB (Qdrant)  │
              └───────────┬───────────┘
                          ▼
        ┌─────────────────────────────────────┐
        │      Hybrid RAG Decision Layer      │
        │                                     │
        │  Score > 0.80 → Internal RAG only  │
        │  Score 0.60–0.80 → Merge both      │  ← gap fixed
        │  Score < 0.60 → General LLM only   │
        └──────┬──────────────────┬───────────┘
               │                  │
       ┌───────▼──────┐   ┌───────▼────────┐
       │ Internal KB  │   │  General LLM   │
       └───────┬──────┘   └───────┬────────┘
               └────────┬─────────┘
                        ▼
              ┌──────────────────┐
              │  Final Response  │
              └──────────────────┘

  ┌──────────────────────────────────────────────────────────┐
  │                    AI PIPELINE                            │
  │                   (Ingestion Side)                        │
  │                                                           │
  │  Connectors → Extraction → Processing → Embeddings →      │
  │  Indexing (Qdrant)                                        │
  │                                                           │
  │  Sources: GitHub · Git URL · Jira · Confluence ·          │
  │           SharePoint · PDF · DOCX · HTML · ZIP            │
  └──────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────┐
  │               ANALYZER SERVICE (Phase 1)                  │
  │  Upload/Clone repo → Read README or folder tree →          │
  │  LLM generates architecture summary                        │
  └──────────────────────────────────────────────────────────┘
```

---

## Hybrid RAG Decision Logic

The decision layer in `Backend/chat_service/rag_engine/decision_layer.py` routes each query through one of three branches based on the top Qdrant similarity score:

| Score Range | Branch | Behavior |
|-------------|--------|----------|
| `> 0.80` | Internal RAG | Answer grounded entirely in your knowledge base |
| `0.60 – 0.80` | Merge | Retrieve internal chunks AND query general LLM; `response_merger.py` blends both into one coherent answer with source labels |
| `< 0.60` | General LLM | Fall back to Claude/GPT with no internal context; answer is flagged as "general knowledge, not from your KB" |

The merge branch (0.60–0.80) gives useful answers even when the KB has partial coverage — the most common real-world case.

---

## Project Structure

```
Engineering_Knowledge_Search_Platform/
│
├── Backend/                              # Query-side services
│   ├── api_gateway/
│   │   ├── main.py                       # FastAPI entry point, middleware wiring
│   │   ├── routes/                       # Route registration
│   │   └── middleware/                   # Auth, rate-limit, logging middleware
│   │
│   ├── auth_service/
│   │   ├── controllers/                  # HTTP handlers
│   │   ├── services/                     # JWT, password hashing logic
│   │   ├── models/                       # SQLAlchemy User model
│   │   └── schemas/                      # Pydantic request/response schemas
│   │
│   ├── search_service/
│   │   ├── semantic_search/              # Query embedding + Qdrant retrieval
│   │   ├── reranking/                    # Cross-encoder re-scoring
│   │   └── search_controller.py
│   │
│   ├── chat_service/
│   │   ├── rag_engine/
│   │   │   ├── retriever.py              # Top-k chunk retrieval
│   │   │   ├── decision_layer.py         # 3-branch score routing (< 0.60 / 0.60-0.80 / > 0.80)
│   │   │   └── response_merger.py        # Blends internal + general LLM for merge branch
│   │   ├── llm_clients/
│   │   │   ├── claude_client.py          # Anthropic Claude (streaming)
│   │   │   └── general_llm_client.py     # Fallback LLM (OpenAI GPT or Claude without context)
│   │   ├── prompt_builder/               # Assembles system + context + history prompts
│   │   └── chat_controller.py
│   │
│   ├── analyzer_service/                 # Phase 1 — Repo Analysis
│   │   ├── controllers/
│   │   ├── services/
│   │   │   └── repo_analyzer.py          # README detection + folder-tree reading
│   │   ├── llm_clients/
│   │   └── prompts/
│   │       └── analyzer_prompts.py       # System + user prompt templates
│   │
│   ├── document_service/
│   │   ├── upload/                       # File validation, storage
│   │   ├── metadata/                     # Document metadata CRUD
│   │   ├── extraction/                   # Text pre-extraction for display
│   │   └── document_controller.py
│   │
│   ├── database/
│   │   └── postgres/                     # SQLAlchemy session, migrations (Alembic)
│   │                                     # Note: Qdrant is owned by AI_pipeline/indexing/
│   └── shared/                           # Cross-service utilities, constants
│
├── AI_pipeline/                          # Ingestion-side pipeline
│   ├── connectors/
│   │   ├── github_connector.py           # GitHub API — repos, issues, PRs
│   │   ├── git_connector.py              # Generic git clone via GitPython
│   │   ├── jira_connector.py             # Jira REST API
│   │   ├── confluence_connector.py       # Confluence REST API
│   │   └── sharepoint_connector.py       # SharePoint / MS Graph API
│   │
│   ├── extraction/
│   │   ├── pdf_extractor.py              # PyMuPDF — text + page metadata
│   │   ├── docx_extractor.py             # python-docx
│   │   ├── html_extractor.py             # BeautifulSoup
│   │   ├── code_extractor.py             # AST / tree-sitter — function-level extraction
│   │   └── zip_extractor.py              # Extract archive, dispatch by file type
│   │
│   ├── processing/
│   │   ├── cleaner.py                    # Whitespace, encoding normalisation
│   │   ├── text_chunker.py               # Recursive token split (512 tok, 50 overlap)
│   │   ├── code_chunker.py               # Function / class level splitting (AST-aware)
│   │   └── metadata_extractor.py         # Infer title, author, date, language
│   │
│   ├── embeddings/
│   │   ├── embedding_model.py            # Model config (OpenAI text-embedding-3-small)
│   │   └── embedding_generator.py        # Batch embed chunks
│   │
│   ├── indexing/
│   │   ├── qdrant_client.py              # Qdrant connection, collection management
│   │   └── index_manager.py              # Upsert, delete-by-project, metadata filters
│   │
│   └── orchestration/
│       ├── ingestion_pipeline.py         # End-to-end: connector → extract → process → embed → index
│       └── scheduler.py                  # APScheduler for periodic re-ingestion
│
├── Frontend/
│   └── src/
│       ├── components/
│       │   ├── Search/
│       │   │   ├── SearchBar.jsx
│       │   │   ├── SearchResults.jsx
│       │   │   └── SearchFilters.jsx
│       │   ├── Chat/
│       │   │   ├── ChatWindow.jsx
│       │   │   ├── MessageBubble.jsx
│       │   │   └── SourceCard.jsx        # Displays source citations
│       │   ├── Documents/
│       │   │   ├── DocumentViewer.jsx
│       │   │   └── UploadDocument.jsx
│       │   └── Admin/
│       │       ├── Dashboard.jsx
│       │       ├── Users.jsx
│       │       ├── Sources.jsx           # Manage ingestion sources
│       │       └── Analytics.jsx
│       ├── pages/
│       │   ├── Home.jsx
│       │   ├── SearchPage.jsx
│       │   ├── ChatPage.jsx
│       │   ├── DocumentsPage.jsx
│       │   └── AdminPage.jsx
│       ├── services/
│       │   ├── api.js                    # Axios base instance + interceptors
│       │   ├── searchApi.js
│       │   └── chatApi.js
│       ├── hooks/                        # Custom React hooks
│       └── context/                      # Auth context, theme context
│
├── uploads/                              # Raw uploaded files (gitignored in prod)
├── infrastructure/                       # Docker, K8s, Terraform configs
├── docs/                                 # Architecture diagrams, ADRs
├── tests/                                # Integration + E2E tests
├── scripts/                              # DB migration, seed, deploy scripts
├── docker-compose.yml
└── README.md
```

---

## Agent Phases

### Phase 1 — Repo Analyzer (`analyzer_service/`)

**Input:** Uploaded `.zip` or a Git URL

**Flow:**
```
Upload or git clone
        │
        ▼
Walk directory tree
        │
        ├── README found? → read full text
        │
        └── No README? → read folder tree (depth 3) +
                         manifest files (package.json,
                         pyproject.toml, go.mod, pom.xml) +
                         top-level source file imports
        │
        ▼
Claude prompt → structured JSON response
  • summary, tech_stack, architecture,
    key_modules, entry_points
```

### Phase 2 — Knowledge Chat (`chat_service/` + `search_service/`)

**Input:** User question + chat history

**Flow:**
```
Question → Embed → Qdrant retrieval
        │
        ▼
decision_layer.py
  Score > 0.80 → Internal RAG
  Score 0.60–0.80 → response_merger.py (blend)
  Score < 0.60 → General LLM
        │
        ▼
Streamed answer + source citations
```

---

## Data Ingestion Strategy

| Source | Connector | Extractor | Chunker |
|--------|-----------|-----------|---------|
| GitHub repo | `github_connector.py` | `code_extractor.py` | `code_chunker.py` |
| Git URL (any) | `git_connector.py` | `code_extractor.py` | `code_chunker.py` |
| ZIP archive | — | `zip_extractor.py` → dispatches | per file type |
| PDF | — | `pdf_extractor.py` | `text_chunker.py` |
| DOCX | — | `docx_extractor.py` | `text_chunker.py` |
| HTML / Confluence | `confluence_connector.py` | `html_extractor.py` | `text_chunker.py` |
| Jira tickets | `jira_connector.py` | inline text | `text_chunker.py` |
| SharePoint | `sharepoint_connector.py` | `docx_extractor.py` / `pdf_extractor.py` | `text_chunker.py` |

---

## Code Repository Ingestion

Code requires **AST-level chunking** — not line-based — to preserve semantic units:

```
git clone / zip extract
        │
        ▼
Filter (skip .git, node_modules, __pycache__, *.lock, binaries)
        │
        ▼
code_extractor.py (per file)
  • Python  → stdlib ast
  • JS/TS   → tree-sitter
  • Java/Go → tree-sitter grammars
        │
        ▼
Semantic units extracted:
  function → 1 chunk  │  class+methods → 1 chunk
  module docstring → 1 chunk
        │
        ▼
Chunk metadata: { file, function_name, class_name, language,
                  start_line, end_line, project_id }
        │
        ▼
Embed → Qdrant
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLAlchemy, Alembic, PostgreSQL |
| Vector DB | Qdrant |
| LLM | Anthropic Claude (primary), OpenAI GPT (general fallback) |
| Embeddings | OpenAI `text-embedding-3-small` |
| Code Parsing | Python `ast`, `tree-sitter` |
| PDF Parsing | PyMuPDF |
| Git Cloning | GitPython |
| Frontend | React 18, Vite, Tailwind CSS |
| Scheduler | APScheduler |
| Containerisation | Docker, Docker Compose |

---

## Getting Started

```bash
git clone <repo-url>
cd Engineering_Knowledge_Search_Platform

cp Backend/.env.example Backend/.env
cp AI_pipeline/.env.example AI_pipeline/.env

docker compose up --build
```

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
SECRET_KEY=change-me
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
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=eksp_knowledge
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE_MB=100
```

---

## API Reference

### Phase 1 — Repo Analysis
```
POST /api/v1/analyze/repo
Body: { project_id, git_url? } or multipart file upload (.zip)

Response: { summary, tech_stack, architecture, key_modules, entry_points, readme_found }
```

### Phase 2 — Chat
```
POST /api/v1/chat
Body: { project_id, message, chat_history[] }

Response (SSE stream):
  event: token  data: { token }
  event: done   data: { sources: [{ file, page, symbol, score }] }
```

### Ingestion
```
POST /api/v1/ingest
Body: { project_id, source_type: "file|zip|git|github|confluence|jira" }
      + files[] or { git_url | github_repo | confluence_space | jira_project }
```
