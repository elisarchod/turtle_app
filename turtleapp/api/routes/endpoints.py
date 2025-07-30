from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from turtleapp.src.utils import logger
from turtleapp.src.workflows.graph import movie_workflow_agent

app = FastAPI(
    title="Turtle App - Home Theater Assistant",
    description="AI-powered home theater management system with multi-agent orchestration"
)


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
def health_check():
    return HealthResponse(
        status="healthy",
        time=datetime.now(),
        uptime="Running"
    )


@app.post("/chat",
          response_model=ChatResponse,
          responses={500: {"model": ErrorResponse}})
def chat(request: ChatRequest):
    return _process_chat_request(request.message, request.thread_id)

def _process_chat_request(message: str, thread_id: Optional[str] = None) -> ChatResponse:
    logger.info(f"Received request: {message}")
    
    try:
        result, used_thread_id = movie_workflow_agent.invoke(message, thread_id)
        
        logger.info(f"Workflow completed successfully for thread: {used_thread_id}")
        
        # Extract response from workflow result
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            response_content = last_message.content
        else:
            response_content = "No response generated"
        
        return ChatResponse(
            response=response_content,
            thread_id=used_thread_id
        )
    
    except Exception as e:
        logger.error(f"Workflow failed: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to process request: {str(e)}"
        )

def main():
    import uvicorn
    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()