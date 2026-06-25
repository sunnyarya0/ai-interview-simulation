import asyncio

from app.db.chroma import get_resume_collection
from app.pipeline.schemas import ResumeProfile


def chunk_profile(profile: ResumeProfile, resume_id: str) -> list[dict]:
    """Break a structured profile into retrievable chunks with section metadata."""
    chunks: list[dict] = []

    for i, exp in enumerate(profile.experience):
        highlights = "; ".join(exp.highlights)
        text = f"Experience: {exp.role} at {exp.company} ({exp.duration}). {highlights}".strip()
        chunks.append({"id": f"{resume_id}:experience:{i}", "text": text, "section": "experience"})

    for i, proj in enumerate(profile.projects):
        tech = ", ".join(proj.technologies)
        text = f"Project: {proj.name}. {proj.description}. Technologies: {tech}".strip()
        chunks.append({"id": f"{resume_id}:project:{i}", "text": text, "section": "project"})

    for i, edu in enumerate(profile.education):
        text = f"Education: {edu.degree} at {edu.institution} ({edu.year})".strip()
        chunks.append({"id": f"{resume_id}:education:{i}", "text": text, "section": "education"})

    skills = ", ".join(profile.skills + profile.technologies)
    if skills:
        chunks.append({"id": f"{resume_id}:skills:0", "text": f"Skills and technologies: {skills}", "section": "skills"})

    # Drop empty/degenerate chunks
    return [c for c in chunks if len(c["text"]) > 12]


def _index_sync(resume_id: str, chunks: list[dict]) -> None:
    collection = get_resume_collection()
    collection.upsert(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[{"resume_id": resume_id, "section": c["section"]} for c in chunks],
    )


async def index_resume(resume_id: str, profile: ResumeProfile) -> int:
    """Chunk a profile and upsert it into Chroma. Returns the number of chunks indexed."""
    chunks = chunk_profile(profile, resume_id)
    if chunks:
        await asyncio.to_thread(_index_sync, resume_id, chunks)
    return len(chunks)


if __name__ == "__main__":
    from app.pipeline.schemas import Experience, Project

    profile = ResumeProfile(
        name="Test",
        skills=["Python", "FastAPI"],
        experience=[Experience(company="Acme", role="ML Engineer", highlights=["Built ML pipelines with PyTorch"])],
        projects=[Project(name="Recommender", description="Movie recommender", technologies=["scikit-learn"])],
    )
    rid = "test-resume-1"
    n = asyncio.run(index_resume(rid, profile))
    print(f"indexed {n} chunks")
    col = get_resume_collection()
    res = col.query(query_texts=["machine learning experience"], where={"resume_id": rid}, n_results=1)
    print("top:", res["documents"][0][0])
    col.delete(where={"resume_id": rid})
