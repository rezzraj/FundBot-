from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
import json

from apps.api.dependencies import get_services, Services

router = APIRouter()


@router.post("/session")
async def create_session(
    request: dict,
    services: Services = Depends(get_services),
):
    """Create a new chat session."""
    profile_id = request.get("profile_id", "anonymous")
    session = services.cloudant.create_chat_session(profile_id)
    return {"session_id": session.get("id", session.get("_id", "")), "status": "created"}


@router.post("/message")
async def send_message(
    request: dict,
    services: Services = Depends(get_services),
):
    """Send a message and get a response (REST endpoint)."""
    session_id = request.get("session_id")
    message = request.get("message", "")

    if not session_id or not message:
        raise HTTPException(status_code=400, detail="session_id and message are required")

    response = await services.agent.process_message(session_id, message)

    return {
        "session_id": session_id,
        "response": response,
    }


@router.post("/message/stream")
async def send_message_stream(
    request: dict,
    services: Services = Depends(get_services),
):
    """SSE endpoint for streaming tool events + response."""
    session_id = request.get("session_id")
    message = request.get("message", "")

    if not session_id or not message:
        raise HTTPException(status_code=400, detail="session_id and message are required")

    async def event_generator():
        events = []

        async def on_event(event_data):
            events.append(event_data)

        import asyncio
        task = asyncio.create_task(
            services.agent.process_message(session_id, message, on_event=on_event)
        )

        last_sent = 0
        while not task.done():
            await asyncio.sleep(0.05)
            while last_sent < len(events):
                yield f"data: {json.dumps(events[last_sent])}\n\n"
                last_sent += 1

        try:
            response = await task
            yield f"data: {json.dumps({'type': 'response', 'content': response})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.websocket("/ws/{session_id}")
async def chat_websocket(
    websocket: WebSocket,
    session_id: str,
):
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()
    services = get_services()

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            user_text = message.get("message", "")

            # Send "thinking" event
            await websocket.send_json({
                "type": "thinking",
                "content": "Analyzing your request...",
            })

            # Define event callback for tool streaming
            async def on_event(event_data: dict):
                await websocket.send_json(event_data)

            # Process through agent
            response = await services.agent.process_message(
                session_id, user_text, on_event=on_event
            )

            # Send response
            await websocket.send_json({
                "type": "response",
                "content": response,
            })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "content": str(e),
        })
