Hi,
this is my first e2e project for levereging the LLM usages
I used langchain as my development platform and thire guidelince for best practice 
the purpose here is not to build the best app but to experiment with many tools as possible

### Usage for the project:

Have a home personal assistant for home theater with different services (call qbitorrnet, sickchill for managing the torrent search )

### Built Langgraph application - Multi-agent supervisor architecture

- Used ReAct agent
- with checkpointers
- tracing
- deployed to langsmith (example for sdk call):
```python
import os
from langgraph.pregel.remote import RemoteGraph
from langgraph_sdk import get_client
from langgraph_sdk import get_sync_client
from dotenv import load_dotenv

load_dotenv(override=True)

LANGSMITH_ENDPOINT = "https://ht-frosty-battery-91-26df676ff73856d48624516684b654c1.us.langgraph.app"
client = get_sync_client(url=LANGSMITH_ENDPOINT, api_key=os.environ["LANGCHAIN_API_KEY"])
GRAPH_NAME = "home_recommender"

client = RemoteGraph(GRAPH_NAME, api_key=os.environ["LANGCHAIN_API_KEY"], url=LANGSMITH_ENDPOINT)

question = "tell me the plot of terminator 4 ?"
config = {"configurable": {"thread_id": "<thread_name>"}}

ans = client.invoke(input={"messages": question}, config=config)

```


### Functionalities used in the project:
- Tools:
  - RAG with pinecone embedding (`retriever_tool`)
  - qbitorrent client - check which movies are downloaded etc, used qbitorrent documentation
  - run python
- **Evaluations & experiments**:
  - rag:
    - Hallucination
    - Relevance
    - Helpfulness
  - Model
- Prompt management in langchain hub

Future:
- Token cost optimization

Had integration with:
- telegram
- ollma / llama


Progress of  with history of movies and their summaries:

- [x] The chatbot should be able to answer questions about movies 
- [x] Persistence - should remember the history of the conversation
- [x] Recommend movies based on user input
- [ ] Support the following tools
    - [x] Get current torrents list
    - [ ] Find torrent online (need to create service for this)
    - [ ] Find file path in torrent list
    - [ ] Download torrent file
    - [ ] Play movie (stream)
    - [ ] pass link to torrent API
- [ ] telegram bot https://github.com/python-telegram-bot/python-telegram-bot?tab=readme-ov-file
- [x] should store conversation history in a database
- [ ] create designated prompts for the user to interact with the bot
- [ ] use self hosted model (llama, deepseek)  

data set from https://paperswithcode.com/dataset/cmu-movie-summary-corpus
https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/#create-tools

