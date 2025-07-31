from langchain_core.tools import BaseTool
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from turtleapp.settings import settings
from turtleapp.src.utils import handle_tool_errors, logger

vector_store: PineconeVectorStore = PineconeVectorStore.from_existing_index(
    index_name=settings.pinecone.index_name,
    embedding=OpenAIEmbeddings(model=settings.openai.embedding_model)
)

def parse_document_content(content: str) -> dict[str, str]:
    return {
        key.strip(): value.strip()
        for field in content.strip().split(' | ')
        if ':' in field
        for key, value in [field.split(':', 1)]
        if key.strip() and value.strip()
    }

class MovieRetrieverTool(BaseTool):
    name: str = "movie_details_retriever"
    description: str = """Search the movie database (42,000+ movies) using semantic search.
    
    Use this tool when users ask about:
    - Movie plots, summaries, or storylines
    - Cast members, directors, or crew
    - Movie recommendations or similar films
    - Genre-based queries or movie details
    - Release years or production information
    
    Input: Search query (movie title, genre, plot keywords, cast names)
    Parameters: max_results (default 5, use 3-5 for specific movies, 5-10 for broad searches)
    
    Example queries:
    - "romantic comedies from the 90s"
    - "Tom Hanks movies"
    - "sci-fi thriller space"
    - "Inception plot summary"
    """

    @handle_tool_errors(default_return="Movie search failed")
    def _run(self, query: str, max_results: int = 5) -> str:
        retriever = vector_store.as_retriever(search_kwargs={"k": max_results})
        
        documents = retriever.invoke(query)
        
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
                plot_preview = plot[:800] + "..." if len(plot) > 800 else plot
                result += f"   Plot: {plot_preview}\n"
            
            result += "\n"
        
        return result

movie_retriever_tool = MovieRetrieverTool()


if __name__ == "__main__":
    query = "a weird movie about dreams"
    logger.info(MovieRetrieverTool()._run(query, max_results=5))