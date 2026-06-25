import asyncio

from sqlalchemy import select

from app.core.logger import logger
from app.db.models import Resume
from app.db.session import AsyncSessionLocal
from app.pipeline.extractor import extract_text
from app.pipeline.indexer import index_resume
from app.pipeline.structurer import structure_resume


async def _set_status(resume_id: str, status: str) -> None:
    async with AsyncSessionLocal() as session:
        resume = await session.get(Resume, resume_id)
        if resume:
            resume.status = status
            await session.commit()


async def process_resume(resume_id: str) -> None:
    """Background task: parse → structure → index a resume, updating status as it goes.

    Runs inside the API event loop via FastAPI BackgroundTasks, so all blocking work
    (pdfplumber, Chroma) is offloaded with asyncio.to_thread.
    """
    logger.info("process_resume started: {}", resume_id)
    async with AsyncSessionLocal() as session:
        resume = await session.get(Resume, resume_id)
        if resume is None:
            logger.error("process_resume: resume {} not found", resume_id)
            return
        resume.status = "processing"
        await session.commit()
        file_path = resume.file_path

    try:
        raw_text = await asyncio.to_thread(extract_text, file_path)
        logger.info("extracted {} chars from {}", len(raw_text), resume_id)

        profile = await structure_resume(raw_text)
        logger.info("structured resume {} (name={!r})", resume_id, profile.name)

        async with AsyncSessionLocal() as session:
            resume = await session.get(Resume, resume_id)
            resume.structured_profile = profile.model_dump()
            await session.commit()

        n = await index_resume(resume_id, profile)
        logger.info("indexed {} chunks for {}", n, resume_id)

        await _set_status(resume_id, "ready")
        logger.info("process_resume done: {} → ready", resume_id)
    except Exception as exc:
        logger.exception("process_resume failed for {}: {}", resume_id, exc)
        await _set_status(resume_id, "failed")
