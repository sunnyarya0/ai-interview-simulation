import asyncio

from app.db.chroma import get_resume_collection


class Retriever:
    """Retrieves the resume chunks most relevant to a query, grounding the
    interviewer's next question (RAG)."""

    def _query_sync(self, query: str, resume_id: str, top_k: int) -> list[str]:
        collection = get_resume_collection()
        result = collection.query(
            query_texts=[query],
            where={"resume_id": resume_id},
            n_results=top_k,
        )
        docs = result.get("documents") or [[]]
        return docs[0]

    async def retrieve(self, query: str, resume_id: str, top_k: int = 3) -> str:
        """Return a formatted context block of the top-k relevant chunks ('' if none)."""
        docs = await asyncio.to_thread(self._query_sync, query, resume_id, top_k)
        if not docs:
            return ""
        bullets = "\n".join(f"- {d}" for d in docs)
        return f"Relevant resume context:\n{bullets}"


if __name__ == "__main__":
    from app.pipeline.indexer import index_resume
    from app.pipeline.schemas import Experience, Project, ResumeProfile

    rid = "retriever-test-1"
    profile = ResumeProfile(
        name="Test",
        skills=["Python", "FastAPI"],
        experience=[Experience(company="Acme", role="Backend Engineer", highlights=["Built REST APIs in Python and FastAPI"])],
        projects=[Project(name="Recsys", description="Recommender", technologies=["PyTorch"])],
    )

    async def _smoke():
        await index_resume(rid, profile)
        block = await Retriever().retrieve("python backend experience", rid)
        print(block)
        assert "Python" in block, "expected relevant chunk in context"
        print(f"\n(context length: {len(block)} chars)")
        get_resume_collection().delete(where={"resume_id": rid})
        print("OK")

    asyncio.run(_smoke())
