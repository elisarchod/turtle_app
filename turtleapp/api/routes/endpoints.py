from fastapi import FastAPI

from turtleapp.src.workflows.graph import movie_workflow_agent

app = FastAPI()


@app.get("/ask-home-agent")
async def ask_home_agent(message: str):
    return movie_workflow_agent.invoke({"message": message})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)