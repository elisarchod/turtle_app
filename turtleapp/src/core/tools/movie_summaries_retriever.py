from langchain_core.tools import Tool
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.tools import BaseTool
from typing import Dict

from turtleapp.settings import settings
from turtleapp.src.utils.error_handler import handle_tool_errors

vector_store: PineconeVectorStore = PineconeVectorStore.from_existing_index(
    index_name=settings.pinecone.index_name,
    embedding=OpenAIEmbeddings(model=settings.openai.embedding_model)
)

def parse_document_content(content: str) -> Dict[str, str]:
    parsed_fields = {}
    
    for line in content.strip().split('\n'):
        line = line.strip()
        if line and ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            if key and value:
                parsed_fields[key] = value
    
    return parsed_fields

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
            parsed_fields = parse_document_content(doc.page_content)
            
            title = parsed_fields.get('title', 'Unknown Title')
            year = parsed_fields.get('release_year', '')
            director = parsed_fields.get('director', '')
            cast = parsed_fields.get('cast', '')
            genre = parsed_fields.get('genre', '')
            plot = parsed_fields.get('plot', '')
            
            year_str = f" ({year})" if year else ""
            result += f"{i}. {title}{year_str}\n"
            
            if director:
                result += f"   Director: {director}\n"
            if cast:
                result += f"   Cast: {cast}\n"
            if genre:
                result += f"   Genre: {genre}\n"
            if plot:
                plot_preview = plot[:300] + "..." if len(plot) > 300 else plot
                result += f"   Plot: {plot_preview}\n"
            
            result += "\n"
        
        return result

movie_retriever_tool: Tool = MovieRetrieverTool()

if __name__ == "__main__":
    query = "Inception"
    print(movie_retriever_tool._run(query, max_results=3))