from fastapi import APIRouter
from pydantic import BaseModel

from chat.rag_engine.response_merger import get_response

router = APIRouter()


class ChatRequest(BaseModel):
    query: str


@router.post("/")
async def chat(request: ChatRequest):
    return await get_response(request.query)