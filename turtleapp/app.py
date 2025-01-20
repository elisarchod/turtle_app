from fastapi import FastAPI

from turtleapp.graph import agent

app = FastAPI()


@app.get("/ask_agent")
async def get_agent(messeage: str):
    return agent.invoke({"message": messeage})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)