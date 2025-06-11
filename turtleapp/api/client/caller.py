import os

from dotenv import load_dotenv
from langgraph.pregel.remote import RemoteGraph
from langgraph_sdk import get_sync_client

load_dotenv(override=True)



LANGSMITH_ENDPOINT=os.environ.get("LANGSMITH_ENDPOINT")
client = get_sync_client(url=LANGSMITH_ENDPOINT, api_key=os.environ["LANGCHAIN_API_KEY"])
GRAPH_NAME = "home_recommender"


client = RemoteGraph(GRAPH_NAME,
                     api_key=os.environ["LANGCHAIN_API_KEY"],
                     url=LANGSMITH_ENDPOINT)

question = "tell me the plot of terminator 4 ?"
config = {"configurable": {"thread_id": "<thread_name>"}}

ans = client.invoke(input={"messages": question},
                    config=config)







