from app.core.logger import logger
from app.pipeline.llm import LLMAdapter
from app.pipeline.schemas import ResumeProfile

_SYSTEM = (
    "You are a precise resume parser. Extract the candidate's information from the "
    "resume text into the required JSON structure. Only use information present in the "
    "text — never invent details. If a field is absent, use an empty string or empty list."
)


async def structure_resume(raw_text: str, llm: LLMAdapter | None = None) -> ResumeProfile:
    """Parse raw resume text into a structured ResumeProfile using schema-constrained LLM output."""
    llm = llm or LLMAdapter()
    content = await llm.complete(
        prompt=f"Resume text:\n\n{raw_text}",
        system=_SYSTEM,
        format=ResumeProfile.model_json_schema(),
        temperature=0,
    )
    try:
        return ResumeProfile.model_validate_json(content)
    except Exception as exc:
        logger.error("Failed to parse structured resume: {}", exc)
        raise ValueError(f"Could not parse resume into ResumeProfile: {exc}") from exc


if __name__ == "__main__":
    import asyncio
    import json
    import sys

    from app.pipeline.extractor import extract_text

    text = extract_text(sys.argv[1]) if len(sys.argv) > 1 else (
        "Jane Doe. Senior Python Engineer. Skills: Python, FastAPI, Kafka. "
        "Experience: Built a real-time data pipeline at Acme Corp using Kafka and Python."
    )
    profile = asyncio.run(structure_resume(text))
    print(json.dumps(profile.model_dump(), indent=2))
