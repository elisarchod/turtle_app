import asyncio
from turtleapp.src.data_pipeline.vector_store.vector_store_manager import MovieDataLoader, PineconeVectorStoreManager
from turtleapp.settings import settings

async def main() -> None:
    loader = MovieDataLoader()
    documents = loader.load_documents(settings.data.movie_plots_path)
    uploader = PineconeVectorStoreManager()
    await uploader.upload_documents(documents)

if __name__ == "__main__":
    asyncio.run(main())