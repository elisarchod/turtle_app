from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from application.workflows.graph import initialize_workflow
from infrastructure.mcp.client.tools import cleanup_mcp_client


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

# Mount static files directory
static_dir = Path(__file__).parent / "static"
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

# Import routes to register them with the app
from interface.api import routes  # noqa: E402, F401
