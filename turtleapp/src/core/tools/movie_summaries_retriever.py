from langchain_core.tools import Tool, create_retriever_tool
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from turtleapp.settings import vector_db_embedding_model_name, vector_db_index_name
from turtleapp.src.utils.log_handler import logger

vector_store: PineconeVectorStore = PineconeVectorStore.from_existing_index(index_name=vector_db_index_name,
                                                                            embedding=OpenAIEmbeddings(model=vector_db_embedding_model_name))

retriever_tool: Tool = create_retriever_tool(vector_store.as_retriever(),
                                       "movie_details_retriever",
                                       "this includes movies plots and meta data for movies i want to know about, "
                                       "this is the only data base for movie plots i want to use", )

if __name__ == '__main__':
    response: str = retriever_tool.invoke({"query": "comedy"})
    logger.info(response) 