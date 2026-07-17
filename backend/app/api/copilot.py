from fastapi import APIRouter, HTTPException

from app.schemas.copilot import CopilotChatRequest, CopilotChatResponse
from app.services.copilot_service import answer_copilot_chat

router = APIRouter()


@router.post("/copilot/chat", response_model=CopilotChatResponse)
async def post_copilot_chat(request: CopilotChatRequest) -> CopilotChatResponse:
    message = " ".join(request.message.strip().split())
    if not message:
        raise HTTPException(status_code=400, detail="Message is required.")

    response = answer_copilot_chat(
        message=message,
        context=request.context,
        history=[item.model_dump() for item in request.history],
        thread_id=request.thread_id,
    )
    return CopilotChatResponse(**response)
