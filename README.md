



data set from https://paperswithcode.com/dataset/cmu-movie-summary-corpus
https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/#create-tools

Run a chatbot with history of movies and their summaries

- [ ] The chatbot should be able to answer questions about movies 
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
- [ ] should store conversation history in a database
- [ ] create designated prompts for the user to interact with the bot

` prompt = ChatPromptTemplate.from_template("tell me a joke about {topic}") `

` hub.push("topic-joke-generator", prompt, new_repo_is_public=False)`

Current project:

- Have a personal, raspberry pie at home with docker compose and different services (qbitorrnet, pi-hole, sickchill)
- Want to have personal assistant that could get movies / summeries from web

Built Langgraph application - Multi-agent supervisor architecture

- Used ReAct agent
- with checkpointers
- tracing

Used API models so it would run faster

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
- Prompt management / HUB

Future:

- Did not use Langgraph CLI/studio
- Token optimization
- multiple steps between tools

Had integration with:

- telegram
- ollma / llama
