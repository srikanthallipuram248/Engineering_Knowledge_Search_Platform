# AGENTS.md — Agent Design Guide

This document covers the design, responsibilities, prompt contracts, extension points, and operational notes for every AI agent in the Engineering Knowledge Search Platform.

---

## Table of Contents

- [Agent Overview](#agent-overview)
- [Agent 1 — Repo Analyzer Agent](#agent-1--repo-analyzer-agent)
- [Agent 2 — Knowledge Chat Agent](#agent-2--knowledge-chat-agent)
- [Shared Interfaces](#shared-interfaces)
- [LLM Client Layer](#llm-client-layer)
- [Prompt Engineering Guidelines](#prompt-engineering-guidelines)
- [Adding a New Agent](#adding-a-new-agent)
- [Operational Notes](#operational-notes)

---

## Agent Overview

| Agent | File | Phase | Trigger | Output |
|-------|------|-------|---------|--------|
| `RepoAnalyzerAgent` | `agents/repo_analyzer_agent.py` | Phase 1 | User uploads/clones a repo | Structured architecture summary |
| `ChatAgent` | `agents/chat_agent.py` | Phase 2 | User sends a chat message | Streamed answer with source citations |

Both agents inherit from `IAgent` (`agents/base.py`) and are orchestrated by a `Service` layer. They never touch HTTP — endpoints call services, services call agents.

```
Endpoint → Service → Agent → (LLM · VectorStore · Ingestion)
```

---

## Agent 1 — Repo Analyzer Agent

**File:** `AI_pipeline/app/agents/repo_analyzer_agent.py`
**Service:** `AI_pipeline/app/services/repo_analysis_service.py`
**Endpoint:** `POST /api/v1/analyze/repo`

### Responsibility

Given a code repository (as a local extracted path), produce a structured summary covering:
- Project purpose
- Detected tech stack
- High-level architecture
- Key modules and their roles
- Recommended onboarding entry points

### Decision Tree

```
repo_path received
      │
      ▼
Does README.md / README.rst / README.txt exist?
      │
   YES ▼                         NO ▼
Read full README             Build folder snapshot
      │                      (max depth 3, skip .git /
      │                       node_modules / __pycache__)
      │                           │
      │                      Read key manifest files:
      │                      package.json, pyproject.toml,
      │                      Cargo.toml, go.mod, pom.xml
      │                           │
      │                      Scan top-level source files
      │                      for imports + class/fn names
      │                           │
      └─────────┬─────────────────┘
                ▼
         Construct LLM prompt
         (see Prompt Contract below)
                │
                ▼
         Parse structured JSON response
                │
                ▼
         Return RepoAnalysisResult
```

### Prompt Contract

**System prompt** (`llm/prompts/repo_analyzer_prompts.py → SYSTEM_PROMPT`):

```
You are a senior software architect. Your job is to analyze a code repository
and produce a clear, accurate, developer-friendly summary.

Always respond with valid JSON matching this schema:
{
  "summary": "string — 2-4 sentences on what the project does",
  "tech_stack": ["list of detected technologies"],
  "architecture": "string — description of structural patterns used",
  "key_modules": [
    { "name": "string", "role": "string" }
  ],
  "entry_points": ["list of files/commands to start exploring"],
  "readme_found": boolean
}

Be factual. Do not invent features not evidenced in the code.
```

**User prompt template:**

```
Analyze the following repository context and produce the JSON summary.

--- README CONTENT (if found) ---
{readme_content}

--- FOLDER STRUCTURE ---
{folder_tree}

--- KEY FILES CONTENT ---
{key_files_content}
```

### Input / Output Schema

```python
# schemas/repo_analyzer.py

class RepoAnalyzeRequest(BaseModel):
    project_id: UUID
    git_url: Optional[HttpUrl] = None   # mutually exclusive with file upload
    # file upload handled as UploadFile in endpoint

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

| Condition | Behavior |
|-----------|----------|
| LLM returns invalid JSON | Retry up to 2 times with stricter prompt; raise `LLMResponseError` if still invalid |
| Repo has no readable files | Return summary noting empty or binary-only repository |
| Git clone fails (bad URL / auth) | Raise `IngestionError` with user-facing message |
| Repo exceeds size limit | Raise `FileSizeLimitError`; limit set in `core/config.py` |

---

## Agent 2 — Knowledge Chat Agent

**File:** `AI_pipeline/app/agents/chat_agent.py`
**Service:** `AI_pipeline/app/services/chat_service.py`
**Endpoint:** `POST /api/v1/chat`

### Responsibility

Answer user questions grounded in the project's ingested documents and code. Supports:
- Policy and process questions (`"What is the leave policy?"`)
- Code structure questions (`"How is authentication implemented?"`)
- Improvement suggestions (`"What can we improve in the payments module?"`)
- Cross-document synthesis (`"Compare the old and new onboarding guides"`)

### RAG Pipeline

```
User Question (+ chat_history)
         │
         ▼
  Embed question with OpenAI
         │
         ▼
  VectorStore.query(
    query_vector,
    filter={"project_id": project_id},
    top_k=20
  )
         │
         ▼
  Reranker.rerank(question, candidates)   ← cross-encoder scores
  → top 5-7 chunks retained
         │
         ▼
  ContextBuilder.build(chunks)
  → formatted context string with source labels
         │
         ▼
  LLM.stream(system_prompt, context, question, history)
         │
         ▼
  Streamed tokens + source list
```

### Prompt Contract

**System prompt** (`llm/prompts/chat_prompts.py → SYSTEM_PROMPT`):

```
You are an internal knowledge assistant for an engineering team.
You answer questions based ONLY on the provided context.
If the answer is not in the context, say: "I don't have enough information
to answer that from the available documents."

Always cite sources using [Source N] notation.
Be concise. Use bullet points for lists. Use code blocks for code snippets.
```

**User prompt template:**

```
Context:
{context}

Chat History:
{chat_history}

Question: {question}

Answer:
```

### Context Window Management

- Max context chunks: 7 (configurable via `RAG_TOP_K` in config)
- Max tokens per chunk: 400
- Total context budget: ~2800 tokens (leaving room for system prompt + output)
- If a chunk exceeds budget, it is trimmed at sentence boundary

### Source Citations

Each answer includes a `sources` array:

```json
{
  "answer": "The leave policy states that...[Source 1]",
  "sources": [
    {
      "source_id": 1,
      "file": "hr/leave_policy_2024.pdf",
      "page": 3,
      "symbol": null,
      "score": 0.91
    },
    {
      "source_id": 2,
      "file": "src/auth/auth_service.py",
      "page": null,
      "symbol": "AuthService.verify_token",
      "score": 0.87
    }
  ]
}
```

### Input / Output Schema

```python
# schemas/chat.py

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    project_id: UUID
    message: str
    chat_history: List[ChatMessage] = []

class SourceCitation(BaseModel):
    source_id: int
    file: str
    page: Optional[int]
    symbol: Optional[str]
    score: float

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceCitation]
```

### Streaming

The `/chat` endpoint returns `text/event-stream` (SSE). Token chunks are emitted as they arrive from Claude. The final event contains the full `sources` list.

```
event: token
data: {"token": "The "}

event: token
data: {"token": "leave policy..."}

event: done
data: {"sources": [...]}
```

---

## Shared Interfaces

### IAgent (`agents/base.py`)

```python
from abc import ABC, abstractmethod
from typing import Any, Dict

class IAgent(ABC):
    @abstractmethod
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent and return a structured result."""
        ...
```

### ILLM (`llm/base.py`)

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator

class ILLM(ABC):
    @abstractmethod
    async def complete(self, system: str, user: str) -> str: ...

    @abstractmethod
    async def stream(self, system: str, user: str) -> AsyncIterator[str]: ...
```

### IVectorStore (`vectorstore/base.py`)

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class IVectorStore(ABC):
    @abstractmethod
    async def upsert(self, chunks: List[Dict[str, Any]]) -> None: ...

    @abstractmethod
    async def query(
        self, vector: List[float], filter: Dict, top_k: int
    ) -> List[Dict[str, Any]]: ...

    @abstractmethod
    async def delete_by_project(self, project_id: str) -> None: ...
```

### IParser (`ingestion/parsers/base.py`)

```python
from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass

@dataclass
class Document:
    content: str
    metadata: dict

class IParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> List[Document]: ...

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]: ...
```

### IChunker (`chunking/base.py`)

```python
from abc import ABC, abstractmethod
from typing import List
from ingestion.parsers.base import Document

class IChunker(ABC):
    @abstractmethod
    def chunk(self, document: Document) -> List[Document]: ...
```

### IEmbedder (`embeddings/base.py`)

```python
from abc import ABC, abstractmethod
from typing import List

class IEmbedder(ABC):
    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]: ...
```

### ILoader (`ingestion/loaders/base.py`)

```python
from abc import ABC, abstractmethod
from typing import List
from pathlib import Path

class ILoader(ABC):
    @abstractmethod
    async def load(self, source: str) -> Path:
        """Download/extract source and return local directory path."""
        ...
```

---

## LLM Client Layer

**File:** `AI_pipeline/app/llm/claude_client.py`

Uses the Anthropic Python SDK with:
- **Prompt caching** on system prompts (saves tokens on repeated calls)
- **Streaming** via `client.messages.stream()`
- **Retry logic** with exponential backoff (3 attempts)
- **Model** configurable via `CLAUDE_MODEL` env var (default: `claude-sonnet-4-6`)

```python
# Key config
model: str = settings.CLAUDE_MODEL        # claude-sonnet-4-6
max_tokens: int = 4096
temperature: float = 0.0                  # deterministic for structured output
```

For structured JSON output (Phase 1), `temperature=0` and a JSON schema is injected into the system prompt. Responses are validated against Pydantic models.

---

## Prompt Engineering Guidelines

1. **System prompts are cached** — keep them stable across calls. Volatile data (context, question) goes in the user turn only.

2. **JSON responses** — always specify the exact schema in the system prompt. Use `"Respond with ONLY valid JSON, no markdown fences"`.

3. **Grounding** — for RAG answers, instruct the model explicitly: `"Answer ONLY from the provided context. Do not hallucinate."` and include a fallback: `"If the context doesn't contain the answer, say so."`.

4. **Few-shot examples** — for Phase 1 architecture summaries, include 1 short example in the system prompt to anchor format and tone.

5. **Token budgeting** — always leave at least 1024 tokens for the model output. Calculate: `system_tokens + context_tokens + history_tokens + 1024 ≤ model_context_limit`.

6. **Chat history pruning** — keep the last N turns that fit within budget. Summarize older turns if conversation grows long.

---

## Adding a New Agent

1. Create `AI_pipeline/app/agents/my_agent.py`
2. Inherit from `IAgent` and implement `run()`
3. Create a service `services/my_agent_service.py` that instantiates and calls it
4. Add schemas in `api/v1/schemas/my_agent.py`
5. Create endpoint `api/v1/endpoints/my_agent.py`
6. Register the router in `api/v1/router.py`
7. Add prompts in `llm/prompts/my_agent_prompts.py`

---

## Operational Notes

### Ingestion Idempotency

Re-ingesting the same file for the same `project_id` deletes old chunks before inserting new ones. The chunk `id` is a hash of `(project_id + file_path + chunk_index)`.

### Vector Store Isolation

Each project's chunks are tagged with `project_id` in metadata. All vector queries apply a metadata filter so projects never see each other's data.

### Rate Limits

- OpenAI Embeddings: batched in groups of 100 chunks per API call
- Claude: max 1 concurrent request per project (queued, not rejected)

### Cold Start

On first run, ChromaDB creates its persist directory automatically. No manual migration needed for development. For production, use a managed vector DB (Pinecone, pgvector) and set the appropriate env vars.

### Logging

All agents emit structured JSON logs via `core/logging.py`:
```json
{
  "timestamp": "2026-06-03T10:00:00Z",
  "level": "INFO",
  "agent": "RepoAnalyzerAgent",
  "project_id": "uuid",
  "event": "analysis_complete",
  "duration_ms": 1240
}
```
