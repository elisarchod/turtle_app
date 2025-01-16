from fastapi import FastAPI

app = FastAPI()


@app.get("/agents/{agent_name}")
async def get_agent(agent_name: str):
    # This is where you'll fetch and return
    # information about the agent with the given name
    # For now, let's return a simple message
    return {"message": f"Agent {agent_name} requested"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)