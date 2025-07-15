from langchain_core.tools import Tool
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.tools import BaseTool

from turtleapp.settings import settings
from turtleapp.src.utils import logger
from turtleapp.src.utils.error_handler import handle_tool_errors

vector_store: PineconeVectorStore = PineconeVectorStore.from_existing_index(
    index_name=settings.pinecone.index_name,
    embedding=OpenAIEmbeddings(model=settings.openai.embedding_model)
)

class MovieRetrieverTool(BaseTool):
    name: str = "movie_details_retriever"
    description: str = "Search and retrieve movie information from the movie database using semantic search"

    @handle_tool_errors(default_return="Movie search failed")
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