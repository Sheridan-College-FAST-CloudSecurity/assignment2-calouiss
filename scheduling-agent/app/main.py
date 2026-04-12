"""FastAPI backend for the course scheduling advisor."""
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.agent import build_agent
from app.models import PlanRequest, ApproveRequest, AdvisorResponse

agent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    print("Building scheduling agent...")
    agent = build_agent()
    print("Agent ready.")
    yield


app = FastAPI(
    title="Course Scheduling Advisor",
    description="LangGraph-based academic scheduling agent",
    version="1.0.0",
    lifespan=lifespan,
)


def _last_text(messages: list) -> str:
    for m in reversed(messages):
        if hasattr(m, 'content') and isinstance(m.content, str) and m.content.strip():
            return m.content.strip()
    return ""


@app.post("/plan", response_model=AdvisorResponse)
async def plan(req: PlanRequest):
    """Start a new scheduling session."""
    thread_id = req.thread_id if req.thread_id != "auto" else str(uuid.uuid4())
    profile = req.student_profile
    config = {"configurable": {"thread_id": thread_id}}

    initial = {
        'messages': [HumanMessage(content=f"Plan my {profile.get('current_term', 'Fall')} semester.")],
        'completed_courses': profile.get('completed_courses', []),
        'current_plan': {},
        'current_term': profile.get('current_term', 'Fall'),
        'approval': ''
    }

    try:
        last_response = ""
        last_state = None
        for event in agent.stream(initial, config, stream_mode="values"):
            last_state = event
            if 'messages' in event and event['messages']:
                last_response = _last_text(event['messages'])

        status = "awaiting_approval"
        if last_state and last_state.get('current_plan'):
            status = "completed"

        return AdvisorResponse(
            thread_id=thread_id,
            status=status,
            response=last_response,
            proposed_semester=last_state.get('current_plan', {}) if last_state else {},
            messages_count=len(last_state.get('messages', [])) if last_state else 0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/approve", response_model=AdvisorResponse)
async def approve(req: ApproveRequest):
    """Approve or reject the proposed semester."""
    if req.decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="decision must be 'approved' or 'rejected'")

    config = {"configurable": {"thread_id": req.thread_id}}
    try:
        last_response = ""
        last_state = None
        for event in agent.stream(
            Command(resume={'approval': req.decision}), config, stream_mode="values"
        ):
            last_state = event
            if 'messages' in event and event['messages']:
                last_response = _last_text(event['messages'])

        status = "completed" if req.decision == "approved" else "awaiting_approval"
        return AdvisorResponse(
            thread_id=req.thread_id,
            status=status,
            response=last_response,
            proposed_semester=last_state.get('current_plan', {}) if last_state else {},
            messages_count=len(last_state.get('messages', [])) if last_state else 0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history/{thread_id}")
async def history(thread_id: str):
    """Retrieve conversation history for a thread."""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = agent.get_state(config)
        if not state or not state.values:
            raise HTTPException(status_code=404, detail="Thread not found")
        messages = [
            {"role": type(m).__name__, "content": m.content if isinstance(m.content, str) else str(m.content)}
            for m in state.values.get('messages', [])
        ]
        return {
            "thread_id": thread_id,
            "messages": messages,
            "current_plan": state.values.get('current_plan', {}),
            "completed_courses": state.values.get('completed_courses', [])
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "scheduling-advisor"}
