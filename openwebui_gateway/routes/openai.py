from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
import json
import uuid

from openwebui_gateway.agent_service import AgentService
from openwebui_gateway.models.schemas import ChatCompletionRequest, ChatCompletionResponse

router = APIRouter(prefix="/v1")
agent_service = AgentService()


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
):
    """OpenAI API compatible chat completions endpoint."""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")

    try:
        if request.stream:
            async def generate():
                async for chunk in agent_service.chat(
                    x_user_id,
                    request.messages[-1].content,
                    model=request.model,
                    stream=True,
                ):
                    data = {
                        "id": str(uuid.uuid4()),
                        "object": "chat.completion.chunk",
                        "model": request.model,
                        "choices": [{"delta": {"content": chunk}}],
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(generate(), media_type="text/event-stream")
        else:
            response = agent_service.chat(
                x_user_id,
                request.messages[-1].content,
                model=request.model,
                stream=False,
            )

            return {
                "id": str(uuid.uuid4()),
                "object": "chat.completion",
                "model": request.model,
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": response,
                        },
                        "finish_reason": "stop",
                    }
                ],
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_models():
    """List available models in OpenAI API format."""
    models = agent_service.get_models()
    return {"object": "list", "data": models}


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "cyan-gateway"}
