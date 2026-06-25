from pydantic import BaseModel, Field


class Experience(BaseModel):
    company: str = ""
    role: str = ""
    duration: str = ""
    highlights: list[str] = Field(default_factory=list)


class Project(BaseModel):
    name: str = ""
    description: str = ""
    technologies: list[str] = Field(default_factory=list)


class Education(BaseModel):
    institution: str = ""
    degree: str = ""
    year: str = ""


class ResumeProfile(BaseModel):
    name: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)


class Assessment(BaseModel):
    score: int = 0  # 0-100
    comment: str = ""


class FeedbackReport(BaseModel):
    overall_score: int = 0  # 0-100
    communication: Assessment = Field(default_factory=Assessment)
    technical: Assessment = Field(default_factory=Assessment)
    resume_knowledge: Assessment = Field(default_factory=Assessment)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
