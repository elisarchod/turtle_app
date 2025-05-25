from fastapi import FastAPI

from turtleapp.src.workflows.graph import home_agent

app = FastAPI()


@app.get("/ask_agent")
async def get_agent(messeage: str):
    return home_agent.invoke({"message": messeage})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)