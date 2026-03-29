from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from turtleapp.src.utils import logger
import turtleapp.src.workflows.graph as _graph_module
from turtleapp.src.workflows.graph import initialize_workflow
from turtleapp.src.mcp.client.tools import cleanup_mcp_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle (startup/shutdown)."""
    # Startup — load MCP tools and build the workflow graph.
    await initialize_workflow()

    yield

    # Shutdown - cleanup MCP HTTP connections
    await cleanup_mcp_client()


app = FastAPI(
    title="Turtle App - Home Theater Assistant",
    description="AI-powered home theater management system with multi-agent orchestration",
    lifespan=lifespan
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


# Mount static files directory
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # Serve index.html at root path
    @app.get("/")
    def read_root():
        from fastapi.responses import FileResponse
        index_path = static_dir / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {"message": "Turtle App API - UI not found"}


def _process_chat_request(message: str, thread_id: Optional[str] = None) -> ChatResponse:
    logger.info(f"Received request: {message}")

    workflow = _graph_module.movie_workflow_agent
    if workflow is None:
        raise HTTPException(status_code=503, detail="Workflow not initialized yet; please retry.")

    try:
        result, used_thread_id = workflow.invoke(message, thread_id)
        
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