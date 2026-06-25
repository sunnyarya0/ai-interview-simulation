from enum import Enum


class InterviewState(str, Enum):
    GREETING = "greeting"     # AI is giving its opening + first question
    LISTENING = "listening"   # waiting for the candidate's audio
    THINKING = "thinking"     # transcribing + retrieving + generating
    SPEAKING = "speaking"     # streaming the AI's spoken reply
    CLOSING = "closing"       # AI is giving its final sign-off
    DONE = "done"             # interview finished
