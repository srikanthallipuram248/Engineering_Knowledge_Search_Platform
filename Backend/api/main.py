import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.postgres.base import Base
from database.postgres.session import engine
import database.postgres.models 

from utils.config import settings

# Routers
from api.routes.auth_routes import router as auth_router
from analysis.controllers import router as analysis_router
from chat.chat_controller import router as chat_router
from chat.rag_engine.bm25_retriever import warm_bm25_cache
from chat.rag_engine.reranker import get_reranker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup/shutdown lifecycle
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("Database connected successfully")

    except Exception as e:
        print(f"Database startup failed: {e}")

    await asyncio.gather(
        asyncio.to_thread(get_reranker),
        asyncio.to_thread(warm_bm25_cache),
    )
    print("Chat retrieval models warmed up")

    yield

    await engine.dispose()
    print("Database connection closed")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ------------------------------------------------------------------
# Middleware
# ------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change in production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

app.include_router(
    auth_router,
    prefix="/api/v1/auth",
)

app.include_router(
    analysis_router,
    prefix="/api/v1/analyze",
)

app.include_router(
    chat_router,
    prefix="/api/v1/chat",
)

# Future routers

# from api.routes.search_routes import router as search_router
# from api.routes.document_routes import router as document_router

# app.include_router(search_router, prefix="/api/v1/search")
# app.include_router(document_router, prefix="/api/v1/documents")


# ------------------------------------------------------------------
# Health Check
# ------------------------------------------------------------------

@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "service": "backend",
        "version": "1.0.0",
    }