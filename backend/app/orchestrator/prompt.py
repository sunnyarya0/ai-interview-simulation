"""Prompt assembly for the AI interviewer. Pure string building — no model calls."""

_INTERVIEWER_RULES = """You are a friendly but sharp technical interviewer conducting a live voice interview.

Rules:
- Ask exactly ONE question at a time. Keep it to 1-3 sentences — this is spoken aloud.
- Ground your questions in the candidate's actual resume and their previous answers.
- Ask natural follow-up questions that probe deeper into what they just said.
- Be conversational and encouraging, not robotic. Do not list multiple questions.
- Never repeat a question you already asked.
- Do not narrate stage directions or use markdown; output only what you would say out loud."""


def _profile_summary(profile: dict) -> str:
    """A compact, always-in-context summary of the candidate (RAG fills in depth per turn)."""
    if not profile:
        return "No structured resume profile is available."

    lines: list[str] = []
    if profile.get("name"):
        lines.append(f"Name: {profile['name']}")

    skills = (profile.get("skills") or []) + (profile.get("technologies") or [])
    if skills:
        lines.append(f"Skills: {', '.join(dict.fromkeys(skills))}")

    roles = [
        f"{e.get('role', '')} at {e.get('company', '')}".strip(" at ")
        for e in profile.get("experience") or []
    ]
    if roles:
        lines.append(f"Experience: {'; '.join(r for r in roles if r)}")

    projects = [p.get("name", "") for p in profile.get("projects") or []]
    if any(projects):
        lines.append(f"Projects: {', '.join(p for p in projects if p)}")

    return "\n".join(lines) or "No structured resume profile is available."


def build_system_prompt(profile: dict) -> str:
    return f"{_INTERVIEWER_RULES}\n\nCandidate profile:\n{_profile_summary(profile)}"


def build_greeting_prompt(profile: dict) -> str:
    name = (profile or {}).get("name") or "the candidate"
    return (
        f"Greet {name} warmly by name in one sentence, briefly say you'll be doing a short "
        "technical interview based on their resume, then ask your first question. "
        "Keep the whole thing under 4 sentences."
    )


def _format_history(history: list[dict]) -> str:
    out = []
    for turn in history:
        speaker = "Interviewer" if turn["speaker"] == "ai" else "Candidate"
        out.append(f"{speaker}: {turn['text']}")
    return "\n".join(out)


def build_turn_prompt(history: list[dict], rag_context: str, last_answer: str) -> str:
    parts: list[str] = []
    if history:
        parts.append("Conversation so far:\n" + _format_history(history))
    if rag_context:
        parts.append(rag_context)
    parts.append(f"The candidate just answered:\n\"{last_answer}\"")
    parts.append(
        "Respond as the interviewer: briefly acknowledge their answer if natural, then ask "
        "your next question (a follow-up on what they said, or move to another resume topic). "
        "One question only."
    )
    return "\n\n".join(parts)


def build_closing_prompt(profile: dict) -> str:
    name = (profile or {}).get("name") or "the candidate"
    return (
        f"The interview is ending. Thank {name} warmly in 1-2 sentences, let them know the "
        "interview is complete and they'll receive feedback shortly. Do not ask another question."
    )


def build_feedback_prompt(transcript: str, profile: dict) -> str:
    return (
        "You are an expert interviewer evaluating a completed technical interview. "
        "Based on the transcript and the candidate's resume, produce a fair, specific, "
        "constructive assessment in the required JSON structure.\n\n"
        f"Candidate profile:\n{_profile_summary(profile)}\n\n"
        f"Interview transcript:\n{transcript}\n\n"
        "Fill in EVERY field:\n"
        "- overall_score: integer 0-100 reflecting overall performance "
        "(approximately the average of the three section scores). Must not be 0 unless the "
        "candidate truly said nothing of value.\n"
        "- communication, technical, resume_knowledge: each an object with an integer score "
        "0-100 and a specific one-to-two sentence comment. resume_knowledge judges how well "
        "their answers matched and expanded on their resume.\n"
        "- strengths, weaknesses, improvements: each a list of 2-4 short, specific points.\n"
        "Base every judgement only on the transcript."
    )


if __name__ == "__main__":
    profile = {
        "name": "Sarah Chen",
        "skills": ["Python", "PyTorch"],
        "technologies": ["Kubernetes"],
        "experience": [{"role": "Senior ML Engineer", "company": "DataCorp"}],
        "projects": [{"name": "RealtimeRecsys"}],
    }
    print("===== SYSTEM =====")
    print(build_system_prompt(profile))
    print("\n===== GREETING =====")
    print(build_greeting_prompt(profile))
    print("\n===== TURN =====")
    history = [
        {"speaker": "ai", "text": "Tell me about your work at DataCorp."},
        {"speaker": "candidate", "text": "I built recommendation systems for 10 million users."},
    ]
    rag = "Relevant resume context:\n- Experience: Senior ML Engineer at DataCorp. Built recommendation systems."
    print(build_turn_prompt(history, rag, "I led the migration to Kubernetes."))
    assert "Kubernetes" in build_turn_prompt(history, rag, "I led the migration to Kubernetes.")
    assert "Relevant resume context" in build_turn_prompt(history, rag, "x")
    print("\nOK")
