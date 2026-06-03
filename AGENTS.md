# AGENTS.md — Agent & Service Design Guide

This document covers the design, flow, prompt contracts, and extension points for every AI-driven service in the Engineering Knowledge Search Platform.

---

## Table of Contents

- [Service Map](#service-map)
- [Hybrid RAG Decision Layer](#hybrid-rag-decision-layer)
- [Phase 1 — Repo Analyzer Service](#phase-1--repo-analyzer-service)
- [Phase 2 — Chat Service (RAG)](#phase-2--chat-service-rag)
- [AI Pipeline — Ingestion](#ai-pipeline--ingestion)
- [Code Repository Ingestion Deep Dive](#code-repository-ingestion-deep-dive)
- [LLM Clients](#llm-clients)
- [Prompt Engineering Guidelines](#prompt-engineering-guidelines)
- [Extending the Platform](#extending-the-platform)

---

## Service Map

```
Backend/
├── api_gateway/            Entry point, middleware (auth, rate-limit, CORS)
├── auth_service/           User registration, login, JWT
├── search_service/         Semantic search — embed query → Qdrant → rerank → return chunks
├── chat_service/           RAG chat — retrieval → decision layer → LLM → stream answer
│   └── rag_engine/
│       ├── decision_layer.py   ← THE core routing logic (3 branches)
│       └── response_merger.py  ← blends internal + general LLM
├── analyzer_service/       Phase 1 — repo upload/clone → architecture summary
└── document_service/       File uploads, metadata, viewer pre-extraction

AI_pipeline/
├── connectors/             Pull content from GitHub, Git, Jira, Confluence, SharePoint
├── extraction/             Parse raw files → text (PDF, DOCX, HTML, code, zip)
├── processing/             Clean + chunk extracted text
├── embeddings/             Batch-embed chunks with OpenAI
├── indexing/               Upsert into Qdrant, manage collections
└── orchestration/          Pipeline coordination + scheduler for re-ingestion
```

---

## Hybrid RAG Decision Layer

**File:** `Backend/chat_service/rag_engine/decision_layer.py`

### The Problem

A simple binary (use KB or don't) fails in practice:
- Internal KB has partial coverage → binary "no match" wastes relevant chunks
- Forcing KB-only gives wrong answers when score is marginally below threshold

### 3-Branch Solution

```
Qdrant top-1 similarity score
          │
          ├── Score > 0.80 ──────────────► Internal RAG only
          │                                 Ground answer entirely in KB chunks
          │                                 High confidence, cite sources
          │
          ├── Score 0.60 – 0.80 ─────────► Merge (response_merger.py)
          │                                 Retrieve top-k internal chunks AND
          │                                 query general LLM in parallel.
          │                                 Merge: internal context prefixed,
          │                                 general LLM provides gap-fill.
          │                                 Label sections: [From your KB] / [General]
          │
          └── Score < 0.60 ─────────────► General LLM only
                                           No internal context injected.
                                           Answer prefixed with:
                                           "This answer is from general knowledge,
                                            not from your team's documents."
```

### `decision_layer.py` contract

```python
class RAGDecision(Enum):
    INTERNAL = "internal"        # score > 0.80
    MERGE    = "merge"           # 0.60 <= score <= 0.80
    GENERAL  = "general"         # score < 0.60

class DecisionLayer:
    HIGH_THRESHOLD: float = 0.80
    LOW_THRESHOLD:  float = 0.60

    def route(self, top_score: float) -> RAGDecision: ...
    async def execute(self, question, chunks, decision) -> ChatResponse: ...
```

### `response_merger.py` contract

For the merge branch:

```python
class ResponseMerger:
    async def merge(
        self,
        question: str,
        internal_chunks: List[Chunk],   # from Qdrant
        general_answer: str,            # from general LLM
    ) -> MergedResponse:
        """
        Returns a unified answer where internal chunks are preferred
        for facts, general LLM fills gaps. Sources are clearly labelled.
        """
```

### Thresholds

Thresholds are configurable via env vars `RAG_HIGH_THRESHOLD` and `RAG_LOW_THRESHOLD`. Start with `0.80 / 0.60`; tune after reviewing real query logs.

---

## Phase 1 — Repo Analyzer Service

**Location:** `Backend/analyzer_service/`
**Endpoint:** `POST /api/v1/analyze/repo`

### Responsibility

Accept a code repository (`.zip` upload or Git URL), understand its structure, and produce a developer-friendly architecture summary using Claude.

### Decision Tree

```
Input: zip upload or git_url
          │
          ▼
   git_connector.py / zip_extractor.py
   → local directory path
          │
          ▼
   Walk tree (depth ≤ 3, skip .git / node_modules / __pycache__ / *.lock)
          │
          ├── README.md / README.rst / README.txt found?
          │       YES → read full content
          │       NO  → build folder snapshot +
          │             read manifest files (package.json, pyproject.toml,
          │             go.mod, Cargo.toml, pom.xml) +
          │             scan top-level source files for imports + signatures
          │
          ▼
   analyzer_prompts.py → construct LLM prompt
          │
          ▼
   claude_client.py → structured JSON response
          │
          ▼
   Validate with Pydantic → return RepoAnalysisResult
```

### Prompt Contract (`analyzer_service/prompts/analyzer_prompts.py`)

**System prompt:**
```
You are a senior software architect. Analyze the provided repository context
and return ONLY valid JSON with no markdown fences, matching this schema:

{
  "summary": "2-4 sentences describing what this project does",
  "tech_stack": ["list", "of", "technologies"],
  "architecture": "description of the structural patterns used",
  "key_modules": [{ "name": "string", "role": "string" }],
  "entry_points": ["file or command to start exploring"],
  "readme_found": true | false
}

Be factual. Do not invent features not evidenced in the provided context.
```

**User prompt:**
```
Analyze this repository and return the JSON summary.

README:
{readme_content_or_NONE}

Folder structure:
{folder_tree}

Key file excerpts:
{key_files_content}
```

### Output Schema

```python
class KeyModule(BaseModel):
    name: str
    role: str

class RepoAnalysisResult(BaseModel):
    project_id: UUID
    summary: str
    tech_stack: List[str]
    architecture: str
    key_modules: List[KeyModule]
    entry_points: List[str]
    readme_found: bool
```

### Error Handling

| Condition | Behaviour |
|-----------|-----------|
| LLM returns invalid JSON | Retry ×2 with stricter prompt; raise `LLMParseError` |
| Git clone fails | Raise `IngestionError` with user-facing message |
| No readable files in repo | Return summary noting empty or binary-only repo |
| Repo exceeds size limit | Raise `FileSizeLimitError` (limit in `.env`) |

---

## Phase 2 — Chat Service (RAG)

**Location:** `Backend/chat_service/`
**Endpoint:** `POST /api/v1/chat` (SSE stream)

### Full Flow

```
User Question + chat_history
        │
        ▼
Embed question (OpenAI text-embedding-3-small)
        │
        ▼
Qdrant query (top_k=20, filter: project_id)
        │
        ▼
Reranker (cross-encoder, top 7 retained)
        │
        ▼
decision_layer.py → branch
        │
  ┌─────┼──────────┐
  ▼     ▼          ▼
 >0.80  0.60-0.80  <0.60
  │        │         │
  ▼        ▼         ▼
Internal  Merge    General
 RAG     (both)     LLM
  │        │         │
  └────────┼─────────┘
           ▼
   prompt_builder/ → final prompt
           │
           ▼
   claude_client.py → stream tokens
           │
           ▼
   SSE: token events → done event (sources)
```

### Prompt Contract

**System prompt (internal RAG branch):**
```
You are an internal knowledge assistant for an engineering team.
Answer based ONLY on the provided context.
If the context does not contain the answer, say: "I don't have enough
information from your team's documents to answer this."
Always cite sources using [Source N] notation.
```

**System prompt (general LLM branch):**
```
You are a helpful assistant. Answer the following question using
your general knowledge. Note: this answer is NOT based on the
user's internal documents.
```

**User prompt template:**
```
Context:
{context_with_source_labels}

Chat History:
{formatted_history}

Question: {question}

Answer:
```

### Source Citation Format

```json
{
  "answer": "The leave policy grants 20 days per year [Source 1]...",
  "answer_source": "internal | merge | general",
  "sources": [
    { "id": 1, "file": "hr/leave_policy.pdf", "page": 4, "score": 0.91 },
    { "id": 2, "file": "src/auth/service.py", "symbol": "AuthService.verify", "score": 0.85 }
  ]
}
```

### Context Window Budget

| Component | Approx tokens |
|-----------|---------------|
| System prompt | ~200 |
| Retrieved chunks (7 × 400) | ~2,800 |
| Chat history (last 4 turns) | ~800 |
| Question | ~100 |
| Output headroom | 1,024 |
| **Total** | **~4,924** |

Fits within Claude's context window. History is pruned if it exceeds the budget.

---

## AI Pipeline — Ingestion

### Orchestration Flow (`orchestration/ingestion_pipeline.py`)

```
Source (connector / upload)
        │
        ▼
1. Connector pulls raw files to local temp dir
        │
        ▼
2. Extractor dispatches by extension:
   .pdf → pdf_extractor   .docx → docx_extractor
   .html → html_extractor  .py/.ts/etc → code_extractor
   .zip → zip_extractor (then recurse into archive)
        │
        ▼
3. Cleaner normalises whitespace, encoding
        │
        ▼
4. Chunker splits by type:
   text/docs → text_chunker (512 tok, 50 overlap)
   code      → code_chunker (function/class level)
        │
        ▼
5. metadata_extractor enriches chunks
   { project_id, source, file_path, language, symbol,
     page, chunk_index, ingested_at }
        │
        ▼
6. embedding_generator batch-embeds (100 chunks per call)
        │
        ▼
7. index_manager upserts into Qdrant
   (chunk id = hash(project_id + file_path + chunk_index)
    → idempotent re-ingestion)
```

### Scheduler (`orchestration/scheduler.py`)

APScheduler jobs for automatic re-ingestion:
- Confluence spaces: every 6 hours
- Jira projects: every 2 hours
- GitHub repos: on push webhook or every 24 hours
- SharePoint: every 12 hours

---

## Code Repository Ingestion Deep Dive

### Why AST-level chunking

| Approach | Problem |
|----------|---------|
| Line-based (512 chars) | Splits functions mid-way; retrieval returns broken context |
| File-level | Too large for embedding window; every query matches the whole file |
| **AST / function-level** | Each chunk is one complete semantic unit; clean retrieval |

### `code_extractor.py` per language

| Language | Parser |
|----------|--------|
| Python | stdlib `ast` — walks `FunctionDef`, `AsyncFunctionDef`, `ClassDef` |
| JavaScript / TypeScript | `tree-sitter-javascript` / `tree-sitter-typescript` |
| Java | `tree-sitter-java` |
| Go | `tree-sitter-go` |
| Rust | `tree-sitter-rust` (optional) |

### `code_chunker.py` splitting rules

1. Each top-level function → 1 chunk
2. Each class + its `__init__` → 1 chunk; each other method → 1 chunk
3. Module-level docstring / comments → 1 chunk
4. Functions > 300 lines → split at logical block boundaries (blank lines between sections)

### Chunk metadata example

```json
{
  "project_id": "abc-123",
  "source_type": "code",
  "file_path": "src/auth/auth_service.py",
  "language": "python",
  "symbol": "AuthService.verify_token",
  "class_name": "AuthService",
  "function_name": "verify_token",
  "start_line": 45,
  "end_line": 72,
  "chunk_index": 3
}
```

---

## LLM Clients

### `chat_service/llm_clients/claude_client.py`

- Anthropic Python SDK, async streaming
- Prompt caching on system prompts (saves ~60% tokens on repeat calls)
- Retry with exponential backoff (3 attempts, base 1s)
- `temperature=0` for factual RAG answers; `temperature=0.3` for merge branch

### `chat_service/llm_clients/general_llm_client.py`

- Default: Claude without internal context injection (same SDK, different system prompt)
- Can be swapped to OpenAI GPT-4o via env var `GENERAL_LLM_PROVIDER=openai`
- Answers are always prefixed with the "general knowledge" disclaimer

---

## Prompt Engineering Guidelines

1. **System prompts are prompt-cached** — keep them static. All dynamic data (context, question, history) goes in the user turn.

2. **JSON output from Phase 1** — set `temperature=0`, instruct `"Respond with ONLY valid JSON, no markdown"`, validate with Pydantic. Retry on parse failure.

3. **Source labels** — always number sources `[Source N]` inline so the UI can linkify them back to the source metadata array.

4. **Merge branch tone** — prompt the model to clearly separate internal facts (`[From your KB]`) from general knowledge (`[General]`). Users must know the difference.

5. **History pruning** — keep the last N turns that fit the token budget. Summarise older turns into a single compressed context line rather than dropping them entirely.

6. **Score transparency** — log the top Qdrant score and the branch taken for every query. This is the primary debugging signal when answers are wrong.

---

## Extending the Platform

### Add a new connector

1. Create `AI_pipeline/connectors/my_connector.py` implementing `pull(config) -> Path`
2. Register it in `orchestration/ingestion_pipeline.py` source dispatch map
3. Add scheduler job in `orchestration/scheduler.py`

### Add a new file extractor

1. Create `AI_pipeline/extraction/my_extractor.py` implementing `extract(path) -> List[Document]`
2. Add extension mapping in `extraction/__init__.py`

### Add a new language to code extraction

1. Install the tree-sitter grammar: `tree-sitter-mylang`
2. Add a language handler in `extraction/code_extractor.py`
3. Extend chunking rules in `processing/code_chunker.py`

### Change the LLM provider

1. Create `chat_service/llm_clients/my_llm_client.py`
2. Implement `complete(system, user) -> str` and `stream(system, user) -> AsyncIterator[str]`
3. Switch the binding via `LLM_PROVIDER` env var in `api_gateway/main.py` dependency injection

### Tune RAG thresholds

Set `RAG_HIGH_THRESHOLD` and `RAG_LOW_THRESHOLD` in `.env`. Monitor branch distribution in logs — if > 40% of queries hit the general branch, your KB coverage is low. If > 90% hit internal, thresholds may be too loose.
