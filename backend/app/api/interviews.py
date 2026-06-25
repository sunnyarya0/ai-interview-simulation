from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.api.schemas import (
    FeedbackResponse,
    InterviewCreateRequest,
    InterviewResponse,
)
from app.core.logger import logger
from app.db.models import Feedback, Interview, Resume
from app.db.session import get_db

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("", response_model=InterviewResponse)
async def create_interview(body: InterviewCreateRequest, db: AsyncSession = Depends(get_db)):
    resume = await db.get(Resume, body.resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    if resume.status != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Resume is not ready (status: {resume.status}).",
        )

    interview = Interview(resume_id=resume.id, status="created")
    db.add(interview)
    await db.commit()
    await db.refresh(interview)
    logger.info("created interview {} for resume {}", interview.id, resume.id)

    return InterviewResponse(
        interview_id=interview.id, resume_id=interview.resume_id, status=interview.status
    )


@router.get("/{interview_id}", response_model=InterviewResponse)
async def get_interview(interview_id: str, db: AsyncSession = Depends(get_db)):
    interview = await db.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found.")
    return InterviewResponse(
        interview_id=interview.id, resume_id=interview.resume_id, status=interview.status
    )


@router.get("/{interview_id}/feedback", response_model=FeedbackResponse)
async def get_feedback(interview_id: str, db: AsyncSession = Depends(get_db)):
    feedback = (
        await db.execute(select(Feedback).where(Feedback.interview_id == interview_id))
    ).scalars().first()
    if feedback is None:
        raise HTTPException(status_code=404, detail="Feedback not ready.")
    return FeedbackResponse(
        interview_id=interview_id,
        overall_score=feedback.overall_score,
        communication=feedback.communication or {},
        technical=feedback.technical or {},
        resume_knowledge=feedback.resume_knowledge or {},
        strengths=feedback.strengths or [],
        weaknesses=feedback.weaknesses or [],
        improvements=feedback.improvements or [],
    )
