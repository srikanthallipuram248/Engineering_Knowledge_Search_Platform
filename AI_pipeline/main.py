from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from controllers.ingestion_controller import router as ingest_router
from controllers.embedding_controller import router as embedding_router
from embeddings.embedding_model import get_embedding_model
from indexing.index_manager import create_collection


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise Qdrant collection on startup
    create_collection()
    # Load embedding model at startup so the first chat request doesn't time out
    get_embedding_model()

    yield


app = FastAPI(
    title="EKSP — AI Pipeline",
    version="1.0.0",
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───
app.include_router(
    ingest_router,
    prefix="/api/v1/ingest",
    tags=["Ingestion"],
)

app.include_router(
    embedding_router,
    prefix="/api/v1/embed",
    tags=["Embeddings"],
)

@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "service": "ai-pipeline",
    }