# Home Theater Personal Assistant

This project is a personal home theater assistant leveraging Large Language Models (LLMs) and LangChain, designed to
interact with various services on my local network (running Docker Compose [repo](https://github.com/Elisarchod/stack))
). The primary goal is experimentation with different LLM tools and integrations, rather than building a
production-ready application. Currently, this is a side project with several planned improvements.

## Overview

The application creates an agent that runs locally and can access several tools:

* **Retrieval Augmented Generation (RAG):** Accesses a Pinecone vector database containing movie details from 2017.
* **Python Function Execution:** Runs simple Python functions.
* **Torrent Client Interaction:** Communicates with a torrent client (qBittorrent).

The assistant aims to provide a unified interface for managing home theater activities, such as retrieving movie
information and controlling torrent downloads.

## Architecture

The application is built using LangChain's LangGraph framework, employing a multi-agent supervisor architecture.

* **Agent:** ReAct agent.
* **Features:** Checkpointing, RAG.
* **Deployment:** Deployed to LangSmith (example SDK call provided below). Currently, only the RAG functionality is
  available on LangSmith.

## Usage

### LangSmith (RAG Only)

The following Python code demonstrates how to interact with the deployed RAG agent on LangSmith to query movie
information:

```python
import os
from langgraph.pregel.remote import RemoteGraph
from langgraph_sdk import get_client
from langgraph_sdk import get_sync_client
from dotenv import load_dotenv

load_dotenv(override=True)

LANGSMITH_ENDPOINT = "[https://ht-frosty-battery-91-26df676ff73856d48624516684b654c1.us.langgraph.app](https://ht-frosty-battery-91-26df676ff73856d48624516684b654c1.us.langgraph.app)" # Replace with your endpoint
client = get_sync_client(url=LANGSMITH_ENDPOINT, api_key=os.environ["LANGCHAIN_API_KEY"])
GRAPH_NAME = "home_recommender" # Replace with your graph name

client = RemoteGraph(GRAPH_NAME, api_key=os.environ["LANGCHAIN_API_KEY"], url=LANGSMITH_ENDPOINT)

question = "tell me the plot of terminator 4 ?"
config = {"configurable": {"thread_id": "<thread_name>"}} # Replace with a thread ID

ans = client.invoke(input={"messages": question}, config=config)
print(ans)