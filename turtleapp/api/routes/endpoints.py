from fastapi import FastAPI

from turtleapp.src.workflows.graph import movie_workflow_agent
from turtleapp.src.utils import logger

app = FastAPI()


@app.get("/ask-home-agent")
async def ask_home_agent(message: str):
    logger.info(f"Received request: {message}")
    result = movie_workflow_agent.invoke({"message": message})
    logger.info(f"Workflow completed successfully")
    return result

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server...")
    uvicorn.run(app)