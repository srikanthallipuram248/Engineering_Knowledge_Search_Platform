from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.postgres.base import Base
from database.postgres.session import engine
import database.postgres.models  # noqa: F401 — registers all models with Base
from utils.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        # DB unavailable — fine for Phase 1 (analyzer doesn't need it)
        pass
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ────────────────────────────────────────────────────────────────
from analysis.controllers import router as analyzer_router

app.include_router(analyzer_router, prefix="/api/v1/analyze", tags=["Analyzer"])

# Uncomment as you implement each service:
# from auth_service.controllers import router as auth_router
# from search_service.search_controller import router as search_router
# from chat_service.chat_controller import router as chat_router
# from document_service.document_controller import router as document_router
# app.include_router(auth_router,     prefix="/api/v1/auth",      tags=["Auth"])
# app.include_router(search_router,   prefix="/api/v1/search",    tags=["Search"])
# app.include_router(chat_router,     prefix="/api/v1/chat",      tags=["Chat"])
# app.include_router(document_router, prefix="/api/v1/documents", tags=["Documents"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": "backend"}
