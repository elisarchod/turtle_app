from datetime import datetime

from fastapi import HTTPException

import application.workflows.graph as _graph_module
from core.utils import logger
from interface.api.app import app
from interface.api.schemas import ChatRequest, ChatResponse, HealthResponse, ErrorResponse


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


def _process_chat_request(message: str, thread_id: str | None = None) -> ChatResponse:
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
        logger.exception(f"Workflow failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process request")
