from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO: initialise Qdrant collection on startup
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


# ── Routers (uncomment as you implement each) ──────────────────────────────
# from orchestration.ingestion_pipeline import router as ingest_router
# app.include_router(ingest_router, prefix="/api/v1/ingest", tags=["Ingestion"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": "ai-pipeline"}
