from collections.abc import Iterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.copilot.contracts import CopilotResponseV1
from app.copilot.orchestrator import get_institutional_copilot_orchestrator, institutional_copilot_enabled
from app.schemas.copilot import CopilotChatRequest

router = APIRouter()


@router.post("/copilot/chat", response_model=CopilotResponseV1)
async def post_copilot_chat(request: CopilotChatRequest) -> CopilotResponseV1:
    if not institutional_copilot_enabled():
        raise HTTPException(status_code=503, detail="The Institutional Copilot feature is disabled.")
    message = " ".join(request.message.strip().split())
    if not message:
        raise HTTPException(status_code=400, detail="Message is required.")

    orchestrator = get_institutional_copilot_orchestrator()
    try:
        return await run_in_threadpool(
            orchestrator.answer,
            message=message,
            context=request.effective_context,
            request_id=request.request_id,
            thread_id=request.thread_id,
            session_context=request.session_context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="The Copilot could not complete this request safely.") from exc


@router.post("/copilot/chat/stream")
async def stream_copilot_chat(request: CopilotChatRequest) -> StreamingResponse:
    if not institutional_copilot_enabled():
        raise HTTPException(status_code=503, detail="The Institutional Copilot feature is disabled.")
    message = " ".join(request.message.strip().split())
    if not message:
        raise HTTPException(status_code=400, detail="Message is required.")
    orchestrator = get_institutional_copilot_orchestrator()

    def ndjson() -> Iterator[str]:
        for event in orchestrator.iter_stream_events(
            message=message,
            context=request.effective_context,
            request_id=request.request_id,
            thread_id=request.thread_id,
            session_context=request.session_context,
        ):
            yield event.model_dump_json(by_alias=True) + "\n"

    return StreamingResponse(
        ndjson(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
