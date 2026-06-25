import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logger import logger
from app.db.models import Interview, Resume
from app.db.session import AsyncSessionLocal
from app.orchestrator.orchestrator import InterviewOrchestrator
from app.workers.feedback import generate_feedback

router = APIRouter(tags=["interview-stream"])


async def _set_status(interview_id: str, status: str, *, started: bool = False, ended: bool = False) -> None:
    async with AsyncSessionLocal() as session:
        interview = await session.get(Interview, interview_id)
        if interview is None:
            return
        interview.status = status
        now = datetime.now(timezone.utc)
        if started:
            interview.started_at = now
        if ended:
            interview.ended_at = now
        await session.commit()


@router.websocket("/interviews/{interview_id}/stream")
async def interview_stream(websocket: WebSocket, interview_id: str):
    # Validate the interview and load the candidate profile before accepting.
    async with AsyncSessionLocal() as session:
        interview = await session.get(Interview, interview_id)
        if interview is None:
            await websocket.close(code=1008)
            return
        resume = await session.get(Resume, interview.resume_id)
        profile = (resume.structured_profile if resume else {}) or {}
        resume_id = interview.resume_id

    await websocket.accept()
    await _set_status(interview_id, "active", started=True)
    logger.info("interview {} connected", interview_id)

    async def send_json(msg: dict) -> None:
        await websocket.send_json(msg)

    async def send_bytes(data: bytes) -> None:
        await websocket.send_bytes(data)

    orch = InterviewOrchestrator(interview_id, resume_id, profile, send_json, send_bytes)

    try:
        await orch.start()
        while True:
            msg = await websocket.receive()
            if msg["type"] == "websocket.disconnect":
                break
            if msg.get("bytes") is not None:
                orch.on_audio(msg["bytes"])
            elif msg.get("text") is not None:
                data = json.loads(msg["text"])
                mtype = data.get("type")
                if mtype == "end_of_utterance":
                    await orch.on_end_of_utterance()
                elif mtype == "end_interview":
                    await orch.on_end_interview()
                    break
                else:
                    logger.warning("interview {} unknown msg type: {}", interview_id, mtype)
    except WebSocketDisconnect:
        logger.info("interview {} disconnected", interview_id)
    except Exception as exc:
        logger.exception("interview {} stream error: {}", interview_id, exc)
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        await _set_status(interview_id, "completed", ended=True)
        # Generate feedback off the socket so closing isn't blocked (~10-20s LLM call).
        asyncio.create_task(generate_feedback(interview_id))
        logger.info("interview {} closed", interview_id)
