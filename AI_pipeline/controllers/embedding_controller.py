import asyncio
from fastapi import APIRouter
from pydantic import BaseModel

from embeddings.embedding_generator import generate_embedding

router = APIRouter()

class EmbeddingRequest(BaseModel):
    text: str

@router.post("/")
async def create_embedding(
    request: EmbeddingRequest
):
    embedding = await asyncio.to_thread(
        generate_embedding, request.text
    )
    return {"embedding": embedding}