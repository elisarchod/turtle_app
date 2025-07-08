from langchain_core.tools import Tool, create_retriever_tool
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.tools import BaseTool
from typing import Dict, Any, List

from turtleapp.settings import settings
from turtleapp.src.utils import logger

vector_store: PineconeVectorStore = PineconeVectorStore.from_existing_index(
    index_name=settings.pinecone.index_name,
    embedding=OpenAIEmbeddings(model=settings.openai.embedding_model)
)

retriever_prompt = """You are a movie expert assistant. 
                        When given a movie name, genre, plot or any movie-related query, you should:
                        1. Search the movie database using relevant keywords from the query
                        2. Retrieve the most relevant movie information available
                        3. Return the results in a clear, structured format including:
                        - Movie title
                        - Release year (if available)
                        - Genre(s)
                        - description/summary
                        - Any other relevant details from the database

                        If no relevant movies are found, clearly state that no matches were found in the database.
                        Focus on providing accurate, helpful information based on what's available in the database."""

class MovieRetrieverTool(BaseTool):
    name: str = "movie_details_retriever"
    description: str = "Search and retrieve movie information from the movie database using semantic search"

    def _run(self, query: str, max_results: int = 5) -> str:
        retriever = vector_store.as_retriever(search_kwargs={"k": max_results})
        
        documents = retriever.get_relevant_documents(query)
        
        if not documents:
            return f"No movies found matching '{query}'"
        
        result = f"Found {len(documents)} movies matching '{query}':\n\n"
        
        for i, doc in enumerate(documents, 1):
            metadata = doc.metadata if hasattr(doc, 'metadata') else {}
            title = metadata.get('title', 'Unknown Title')
            year = metadata.get('year', '')
            year_str = f" ({year})" if year else ""
            
            result += f"{i}. {title}{year_str}\n"
            result += f"   {doc.page_content[:200]}...\n\n"
        
        return result

movie_retriever_tool: Tool = MovieRetrieverTool() 