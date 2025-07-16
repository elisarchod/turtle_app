from datetime import time
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uuid
from typing import Optional

from turtleapp.src.workflows.graph import movie_workflow_agent
from turtleapp.src.constants import ConfigKeys
from turtleapp.src.utils import logger

app = FastAPI(
    title="Turtle App - Home Theater Assistant",
    description="AI-powered home theater management system with multi-agent orchestration"
)

def create_thread_id() -> str:
    """Generate a unique thread ID with datetime prefix and UUID."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    uuid_part = str(uuid.uuid4())[:8]  # Use first 8 chars of UUID for brevity
    return f"{timestamp}_{uuid_part}"

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's message or question", min_length=1)
    thread_id: Optional[str] = Field(None, description="Optional thread ID for conversation continuity")

class ChatResponse(BaseModel):
    response: str = Field(..., description="The assistant's response")
    thread_id: str = Field(..., description="Thread ID for conversation continuity")
    
class HealthResponse(BaseModel):
    status: str = Field(..., description="API health status")
    time: datetime = Field(..., description="Current server time")
    uptime: str = Field(..., description="API uptime information")
    
class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        time=datetime.now(),
        uptime="Running"
    )



@app.post("/chat", response_model=ChatResponse, responses={500: {"model": ErrorResponse}})
async def chat(request: ChatRequest):
    return await _process_chat_request(request.message, request.thread_id)

async def _process_chat_request(message: str, thread_id: Optional[str] = None) -> ChatResponse:
    logger.info(f"Received request: {message}")
    
    try:
        if not thread_id:
            thread_id = create_thread_id()
        
        config = {ConfigKeys.CONFIGURABLE.value: {ConfigKeys.THREAD_ID.value: thread_id}}
        
        result = await movie_workflow_agent.ainvoke({ConfigKeys.MESSAGES.value: message}, config=config)
        logger.info(f"Workflow completed successfully for thread: {thread_id}")
        
        # Extract response from workflow result
        messages = result.get(ConfigKeys.MESSAGES.value, [])
        if messages:
            last_message = messages[-1]
            response_content = last_message.content
        else:
            response_content = "No response generated"
        
        return ChatResponse(
            response=response_content,
            thread_id=thread_id
        )
    
    except Exception as e:
        logger.error(f"Workflow failed: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to process request: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)