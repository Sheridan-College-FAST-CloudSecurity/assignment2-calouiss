"""Pydantic models for the FastAPI scheduling advisor API."""
from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    student_profile: dict = Field(..., description="Student profile with completed_courses and current_term")
    thread_id: str = Field(default="auto", description="Conversation thread ID — use 'auto' to generate one")


class ApproveRequest(BaseModel):
    thread_id: str = Field(..., description="Thread ID of the paused session")
    decision: str = Field(..., description="'approved' or 'rejected'")


class AdvisorResponse(BaseModel):
    thread_id: str
    status: str = Field(description="completed, awaiting_approval, or error")
    response: str = Field(default="")
    proposed_semester: dict = Field(default_factory=dict)
    messages_count: int = Field(default=0)
