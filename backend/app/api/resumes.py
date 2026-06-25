import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ResumeStatusResponse, ResumeUploadResponse
from app.core.config import settings
from app.core.logger import logger
from app.db.models import Resume
from app.db.session import get_db
from app.workers.resume import process_resume

router = APIRouter(prefix="/resumes", tags=["resumes"])

# Magic-byte signatures: PDF starts with %PDF, DOCX is a ZIP (PK\x03\x04)
_SIGNATURES = {
    b"%PDF": ".pdf",
    b"PK\x03\x04": ".docx",
}


def _detect_ext(head: bytes) -> str | None:
    for sig, ext in _SIGNATURES.items():
        if head.startswith(sig):
            return ext
    return None


@router.post("", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    ext = _detect_ext(content[:8])
    if ext is None:
        raise HTTPException(status_code=422, detail="Only PDF and DOCX files are supported.")

    resume_id = str(uuid.uuid4())
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{resume_id}{ext}"
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    resume = Resume(
        id=resume_id,
        filename=file.filename or f"resume{ext}",
        file_path=str(file_path),
        status="uploaded",
    )
    db.add(resume)
    await db.commit()
    logger.info("uploaded resume {} ({})", resume_id, file.filename)

    background_tasks.add_task(process_resume, resume_id)
    return ResumeUploadResponse(resume_id=resume_id, status="uploaded")


@router.get("/{resume_id}/status", response_model=ResumeStatusResponse)
async def get_resume_status(resume_id: str, db: AsyncSession = Depends(get_db)):
    resume = await db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return ResumeStatusResponse(resume_id=resume.id, status=resume.status)
