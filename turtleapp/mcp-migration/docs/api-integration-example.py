from typing import Optional
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import sys
from pathlib import Path
mcp_client_path = Path(__file__).parent.parent / "client-integration"
sys.path.insert(0, str(mcp_client_path))

from sync_mcp_client import SyncMCPClient

# Request/Response models (unchanged from existing API)
class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    thread_id: Optional[str] = None

# Router setup
router = APIRouter()

# Initialize MCP client (could be done at module level for reuse)
mcp_client = SyncMCPClient()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        response_text = mcp_client.process_message(
            message=request.message,
            thread_id=request.thread_id
        )
        
        return ChatResponse(
            response=response_text,
            thread_id=request.thread_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat message: {str(e)}"
        )

@router.get("/health")
async def health_check():
    try:
        mcp_client.process_message("test")
        
        return {
            "status": "healthy",
            "mcp_client": "operational",
            "available_tools": mcp_client.get_available_tools()
        }
    except Exception as e:
        return {
            "status": "degraded", 
            "mcp_client": f"error: {str(e)}",
            "available_tools": []
        }

# Example usage for testing
if __name__ == "__main__":
    import asyncio
    
    async def test_endpoint():
        """Test the chat endpoint with sample queries."""
        test_queries = [
            "Tell me about action movies",
            "Download Terminator 2", 
            "Check my download status",
            "Scan my movie library"
        ]
        
        for query in test_queries:
            print(f"\nTesting: {query}")
            request = ChatRequest(message=query)
            try:
                response = await chat_endpoint(request)
                print(f"Response: {response.response[:100]}...")
            except Exception as e:
                print(f"Error: {e}")
    
    print("Testing MCP API Integration:")
    asyncio.run(test_endpoint())