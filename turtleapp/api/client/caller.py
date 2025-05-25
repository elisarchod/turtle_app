import os
import requests
from langgraph.pregel.remote import RemoteGraph
from langgraph_sdk import get_client
from langgraph_sdk import get_sync_client
from dotenv import load_dotenv
load_dotenv(override=True)



LANGSMITH_ENDPOINT="https://ht-frosty-battery-91-26df676ff73856d48624516684b654c1.us.langgraph.app"
client = get_sync_client(url=LANGSMITH_ENDPOINT, api_key=os.environ["LANGCHAIN_API_KEY"])
GRAPH_NAME = "home_recommender"


client = RemoteGraph(GRAPH_NAME,
                     api_key=os.environ["LANGCHAIN_API_KEY"],
                     url=LANGSMITH_ENDPOINT)

question = "tell me the plot of terminator 4 ?"
config = {"configurable": {"thread_id": "<thread_name>"}}

ans = client.invoke(input={"messages": question},
                    config=config)

# set the LANGSMITH_API_KEY environment variable (create key in settings)
# from langchain import hub
# hub.pull("supervisor_prompt_with_placeholder")

# assistant_id = "493dfefb-eb8d-4f81-aef2-cc60c3fe974f"
# client.assistants.get(assistant_id=assistant_id)
# assistant = client.assistants.get(assistant_id=assistant_id)





