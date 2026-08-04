import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.events import bus

router = APIRouter(tags=["stream"])

KEEPALIVE_S = 25


@router.get("/stream")
async def stream(request: Request) -> StreamingResponse:
    """Server-Sent Events feed of change topics. The kiosk and phones listen
    here and refetch whichever slice changed."""

    async def generator():
        q = bus.subscribe()
        try:
            yield f"data: {json.dumps({'topic': 'hello'})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    topic = await asyncio.wait_for(q.get(), timeout=KEEPALIVE_S)
                    yield f"data: {json.dumps({'topic': topic})}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            bus.unsubscribe(q)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
