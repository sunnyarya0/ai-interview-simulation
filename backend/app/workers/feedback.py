from sqlalchemy import select

from app.core.logger import logger
from app.db.models import Feedback, Interview, Resume, TranscriptTurn
from app.db.session import AsyncSessionLocal
from app.orchestrator.prompt import build_feedback_prompt
from app.pipeline.llm import LLMAdapter
from app.pipeline.schemas import FeedbackReport


async def generate_feedback(interview_id: str) -> None:
    """Evaluate a completed interview and store a structured Feedback row.
    Triggered fire-and-forget (asyncio.create_task) when the interview ends."""
    logger.info("generate_feedback started: {}", interview_id)

    async with AsyncSessionLocal() as session:
        interview = await session.get(Interview, interview_id)
        if interview is None:
            logger.error("generate_feedback: interview {} not found", interview_id)
            return
        existing = (
            await session.execute(select(Feedback).where(Feedback.interview_id == interview_id))
        ).scalars().first()
        if existing is not None:
            logger.info("feedback already exists for {}", interview_id)
            return

        turns = (
            await session.execute(
                select(TranscriptTurn)
                .where(TranscriptTurn.interview_id == interview_id)
                .order_by(TranscriptTurn.turn_index)
            )
        ).scalars().all()
        resume = await session.get(Resume, interview.resume_id)
        profile = (resume.structured_profile if resume else {}) or {}

    if not turns:
        logger.warning("generate_feedback: no transcript for {}, skipping", interview_id)
        return

    transcript = "\n".join(
        f"{'Interviewer' if t.speaker == 'ai' else 'Candidate'}: {t.text}" for t in turns
    )

    try:
        content = await LLMAdapter().complete(
            prompt=build_feedback_prompt(transcript, profile),
            format=FeedbackReport.model_json_schema(),
            temperature=0,
        )
        report = FeedbackReport.model_validate_json(content)
    except Exception as exc:
        logger.exception("generate_feedback failed for {}: {}", interview_id, exc)
        return

    async with AsyncSessionLocal() as session:
        session.add(
            Feedback(
                interview_id=interview_id,
                overall_score=report.overall_score,
                communication=report.communication.model_dump(),
                technical=report.technical.model_dump(),
                resume_knowledge=report.resume_knowledge.model_dump(),
                strengths=report.strengths,
                weaknesses=report.weaknesses,
                improvements=report.improvements,
            )
        )
        await session.commit()
    logger.info("feedback generated for {} (overall_score={})", interview_id, report.overall_score)
