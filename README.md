# Course Scheduling Advisor
**INFO56817 — Generative AI Security | Assignment 2**

## Overview
An AI-powered academic course scheduling agent built with LangGraph and Amazon Bedrock. Plans two consecutive semesters (Fall and Winter) with prerequisite checking, human-in-the-loop approval, and cross-semester memory.

## What I Built

### Part 1 — Tools
- `get_program_requirements` — returns core/elective courses and credit targets
- `check_prerequisites` — validates prerequisites and corequisites
- `get_course_availability` — checks if a course is offered in a given term
- `check_schedule_conflicts` — validates a full proposed semester schedule

### Part 2 — LangGraph Agent
- Full ReAct loop with agent, tool, validation, HITL, finalize, revision nodes
- Back-edges for replanning on rejection or constraint violations
- `MemorySaver` + `thread_id` for cross-semester memory
- Human-in-the-loop approval using `interrupt_before` and `Command(resume=...)`

### Part 3 — Model Comparison
Tested 3 Amazon Bedrock models on Student B (catch-up scenario):
- **Model 1:** `mistral.mistral-large-2402-v1:0`
- **Model 2:** `amazon.nova-lite-v1:0`
- **Model 3:** `mistral.mistral-small-2402-v1:0`

### Part 4 — FastAPI Backend
- `POST /plan` — start a new scheduling session
- `POST /approve` — approve or reject a proposed semester
- `GET /history/{thread_id}` — retrieve conversation history
- `GET /health` — health check

### Bonus — Docker
Dockerized the FastAPI app for local and cloud deployment.

## Tech Stack
- LangGraph + LangChain AWS
- Amazon Bedrock (Converse API)
- FastAPI + Uvicorn
- Pydantic v2
- Docker

## Setup
See `INSTALL.md` for full instructions.