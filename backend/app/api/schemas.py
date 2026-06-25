from pydantic import BaseModel


class ResumeUploadResponse(BaseModel):
    resume_id: str
    status: str


class ResumeStatusResponse(BaseModel):
    resume_id: str
    status: str


class InterviewCreateRequest(BaseModel):
    resume_id: str


class InterviewResponse(BaseModel):
    interview_id: str
    resume_id: str
    status: str


class FeedbackResponse(BaseModel):
    interview_id: str
    overall_score: int
    communication: dict
    technical: dict
    resume_knowledge: dict
    strengths: list[str]
    weaknesses: list[str]
    improvements: list[str]
