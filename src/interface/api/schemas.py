from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's message or question", min_length=1)
    thread_id: str | None = Field(None, description="Optional thread ID for conversation continuity")


class ChatResponse(BaseModel):
    response: str = Field(..., description="The assistant's response")
    thread_id: str = Field(..., description="Thread ID for conversation continuity")


class HealthResponse(BaseModel):
    status: str = Field(..., description="API health status")
    time: datetime = Field(..., description="Current server time")
    uptime: str = Field(..., description="API uptime information")


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    detail: str | None = Field(None, description="Additional error details")
