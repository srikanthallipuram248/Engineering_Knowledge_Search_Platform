from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from controllers.ingestion_controller import router as ingest_router
from indexing.index_manager import create_collection


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise Qdrant collection on startup
    create_collection()

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


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "service": "ai-pipeline",
    }