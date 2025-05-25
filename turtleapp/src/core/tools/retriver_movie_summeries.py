import os
from langchain_core.tools import Tool, create_retriever_tool
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from turtleapp.configuration import embedding_model, index_name

vector_store: PineconeVectorStore = PineconeVectorStore.from_existing_index(index_name=index_name,
                                                                            embedding=OpenAIEmbeddings(model=embedding_model))

retriever_tool: Tool = create_retriever_tool(vector_store.as_retriever(),
                                       "movie_plots_tool",
                                       "this includes movies plots and meta data for movies i want to know about, "
                                       "this is the only data base for movie plots i want to use", )

if __name__ == '__main__':
    response: str = retriever_tool.invoke({"query": "comedy"})
