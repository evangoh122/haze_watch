"""Chat endpoint: grounded, guardrailed analyst assistant.

POST /api/v1/chat - one conversational turn. Responses always carry the research
disclaimer and the provenance sources behind the answer.
"""

from fastapi import APIRouter

from app.llm.service import chat
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def post_chat(request: ChatRequest) -> ChatResponse:
    result = chat([message.model_dump() for message in request.messages])
    return ChatResponse(**result)
