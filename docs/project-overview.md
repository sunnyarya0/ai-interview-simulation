# AI Interview Simulator

## Project Vision
Build a simple AI-powered interview platform where a candidate can upload their resume, join a real-time conversational interview with an AI interviewer, and receive detailed feedback after the interview.

The first version should prioritize simplicity, speed, and a complete end-to-end user experience. Every feature should directly contribute to the core interview workflow, avoiding unnecessary complexity.

## 1. MVP Objective
The objective of Version 1 is to validate the complete interview experience by enabling a user to:
1. Upload a resume.
2. Start an AI interview.
3. Join a conversational meeting (similar to Google Meet).
4. Complete the interview through voice conversaion.
5. Receive AI-generated feedback.
This version is intended to prove the core product experience, not to be feature-complete.

## 2. MVP Workflow
Upload Resume
        │
        ▼
Resume Processing
        │
        ▼
Start Interview
        │
        ▼
Join AI Conversation
(Video/Audio Meeting)
        │
        ▼
Real-time Interview
        │
        ▼
Interview Ends
        │
        ▼
AI Evaluation
        │
        ▼
Feedback Report

## 3. Functional Requirements
### 3.1 Resume Upload

**Description**

The user uploads a resume before starting the interview.

**Input**
- PDF 
- DOCX

**Expected Output**

Extract and structure:

- Candidate information
- Skills
- Experience
- Education
- Projects
- Technologies

This information becomes the interview context.

### 3.2 Start Interview

After successful resume processing, the user clicks:

`Start Interview`

The backend prepares the interview session and initializes all required components.

### 3.3 Conversational Interview

The user joins an interview room similar to a Google Meet call.

The AI interviewer should:

- Speak naturally
- Listen continuously
- Ask one question at a time
- Ask follow-up questions
- Use resume context
- Maintain conversation history
- End the interview naturally

The experience should feel like talking to a real interviewer rather than chatting with a chatbot.

### 3.4 Feedback Generation

After the interview ends, the platform generates a feedback report containing:

- Overall Score
- Communication Assessment
- Technical Assessment
- Resume Knowledge
- Strengths
- Weaknesses
- Suggested Improvements

## 4. Technology Stack
**Frontend** 

| Component     | Technology       |
| ------------- | ---------------- |
| Framework     | Vue.js           |
| Styling       | Tailwind CSS     |
| Communication | HTTP + WebSocket |
| Audio/Video   | WebRTC           |


**Backend**

| Component               | Technology        |
| ----------------------- | ----------------- |
| Language                | Python            |
| Framework               | FastAPI           |
| REST APIs               | FastAPI HTTP      |
| Real-time Communication | FastAPI WebSocket |

**Database**

**Relational Database (Current)**

SQLite

Purpose:

- Interview metadata
- Session information
- Resume metadata
- Feedback storage

**Vector Database**

Chroma

Purpose:
- Resume emgeddings
- Semantic search
- Retrieval during interview

**Large Language Model**

**Local open-source models**

Examples:

- Gemma
- Qwen
- Phi
- Llama (small variants)

Requirements:

- Runs locally
- Low latency
- Small memory footprint
- Good conversational ability

## 5. High-Level Architecture

                 Vue.js Frontend
                        │
         HTTP APIs + WebSocket
                        │
                 FastAPI Backend
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
    SQLite         Chroma DB      Local LLM
        │               │               │
        └───────────────┼───────────────┘
                        │
                Interview Engine
                        │
                 Feedback Generator

## 6. Version 1 Success Criteria

The MVP will be considered successful if a user can:
- Upload a resume without errors.
- Start an interview with a single click.
- Join a real-time AI conversational session.
- Complete the interview through natural voice interaction.
- Receive a personalized feedback report at the end.
- Experience the complete workflow without human intervention.