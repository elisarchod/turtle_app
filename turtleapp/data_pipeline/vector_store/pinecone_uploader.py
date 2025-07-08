import asyncio
import logging
from turtleapp.data_pipeline.vector_store.uploader import DocumentLoader, PineconeUploader
from turtleapp.settings import settings

logger = logging.getLogger(__name__)

async def main() -> None:
    loader = DocumentLoader()
    documents = loader.load_documents(
        settings.data.processed_dir / "wiki_movie_plots_cleaned.csv"
    )
    
    uploader = PineconeUploader()
    await uploader.upload_documents(documents)

if __name__ == "__main__":
    asyncio.run(main())