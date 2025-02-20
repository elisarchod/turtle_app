````markdown
# Home Theater Personal Assistant

This project is a personal home theater assistant leveraging Large Language Models (LLMs) and LangChain, designed to interact with various services on my local network (running Docker Compose [repo](https://github.com/Elisarchod/stack))
 ).  The primary goal is experimentation with different LLM tools and integrations, rather than building a production-ready application.  Currently, this is a side project with several planned improvements.

## Overview

The application creates an agent that runs locally and can access several tools:

*   **Retrieval Augmented Generation (RAG):** Accesses a Pinecone vector database containing movie details from 2017.
*   **Python Function Execution:** Runs simple Python functions.
*   **Torrent Client Interaction:** Communicates with a torrent client (qBittorrent).

The assistant aims to provide a unified interface for managing home theater activities, such as retrieving movie information and controlling torrent downloads.

## Architecture

The application is built using LangChain's LangGraph framework, employing a multi-agent supervisor architecture.

*   **Agent:** ReAct agent.
*   **Features:** Checkpointing, RAG.
*   **Deployment:** Deployed to LangSmith (example SDK call provided below).  Currently, only the RAG functionality is available on LangSmith.

## Usage

### LangSmith (RAG Only)

The following Python code demonstrates how to interact with the deployed RAG agent on LangSmith to query movie information:

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
````

**Note:**  Remember to replace placeholders like `LANGSMITH_ENDPOINT`, `GRAPH_NAME`, and `thread_id` with your actual values.  Also, ensure you have the necessary environment variables set (e.g., `LANGCHAIN_API_KEY`).

### Local Deployment (Full Functionality)

Instructions for local deployment and running the full application with all tools will be provided in a future update.  This will likely involve setting up the Docker Compose environment on your Raspberry Pi.

## Functionalities

### Tools

  * **RAG:** Pinecone vector database (`retriever_tool`).
  * **Torrent Client:** qBittorrent (interaction details based on qBittorrent's documentation).
  * **Python Execution:**  Ability to run arbitrary Python code.

### Evaluations & Experiments

The project includes plans for evaluating and experimenting with:

  * **RAG:** Hallucination, Relevance, Helpfulness.
  * **LLM:** Model performance.
  * **Prompt Management:** Utilizing LangChain Hub for prompt engineering.

### Integrations

  * **Telegram:** Planned integration with a Telegram bot (using `python-telegram-bot`).
  * **Ollama/Llama:** Planned integration with self-hosted LLMs.

## Current Progress and Future Plans

### Core Functionality

  * [x] Chatbot answers questions about movies.
  * [x] Conversation history persistence.
  * [x] Movie recommendations based on user input.

### Torrent Management

  * [x] Retrieve current torrent list.
  * [ ] Find torrents online (requires a dedicated service).
  * [ ] Find file paths within torrents.
  * [ ] Download torrent files.
  * [ ] Play/stream movies.
  * [ ] Pass torrent links to the API.

### Integrations and Enhancements

  * [ ] Telegram bot integration.
  * [x] Store conversation history in a database.
  * [ ] Create designated user interaction prompts.
  * [ ] Integrate self-hosted LLMs (Llama, DeepSeek).
  * [ ] Token cost optimization.

## Dataset

Movie summary data is sourced from the CMU Movie Summary Corpus ([https://paperswithcode.com/dataset/cmu-movie-summary-corpus](https://paperswithcode.com/dataset/cmu-movie-summary-corpus)).

## Resources

  * LangChain: [https://langchain-ai.github.io/langchain/](https://www.google.com/url?sa=E&source=gmail&q=https://langchain-ai.github.io/langchain/)
  * LangGraph Multi-Agent Tutorial: [https://langchain-ai.github.io/langgraph/tutorials/multi\_agent/agent\_supervisor/](https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/)
  * python-telegram-bot: [https://github.com/python-telegram-bot/python-telegram-bot?tab=readme-ov-file](https://github.com/python-telegram-bot/python-telegram-bot?tab=readme-ov-file)

<!-- end list -->

```

Key changes and additions:

*   **Clearer Structure:**  Uses headings and subheadings for better readability.
*   **Concise Language:**  More professional and less conversational tone.
*   **Emphasis on Architecture:**  Explains the multi-agent setup.
*   **Detailed Usage Instructions:** Provides a complete example of how to use the LangSmith deployment.
*   **Organized Functionality List:** Uses checkboxes for progress tracking.
*   **Links to Resources:** Includes important links for LangChain, the dataset, and the Telegram bot library.
*   **Future Plans:**  Clearly outlines the project's roadmap.
*   **Removed Redundancy:**  Eliminated unnecessary phrases and repetitions.
*   **Focus on Technical Details:** Emphasized the technical aspects of the project.

This revised README provides a much more professional and comprehensive overview of your project. Remember to keep it updated as you make progress.  Adding a section on how to set up the local environment will be crucial for anyone who wants to run the full application.
```
