from langchain_core.tools import Tool, create_retriever_tool
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from turtleapp.settings import settings
from turtleapp.src.utils.log_handler import logger

vector_store: PineconeVectorStore = PineconeVectorStore.from_existing_index(
    index_name=settings.pinecone.index_name,
    embedding=OpenAIEmbeddings(model=settings.openai.embedding_model)
)

retriever_prompt = "Retrieve movie summaries from vector database"

retriever_tool: Tool = create_retriever_tool(
    vector_store.as_retriever(),
    "movie_details_retriever",
    retriever_prompt
)

if __name__ == '__main__':
    response: str = retriever_tool.invoke({"query": "comedy"})
    logger.info(response) 