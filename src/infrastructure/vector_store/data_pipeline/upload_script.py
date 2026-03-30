import asyncio
from infrastructure.vector_store.data_pipeline.loader import MovieDataLoader
from infrastructure.vector_store.data_pipeline.manager import PineconeVectorStoreManager
from infrastructure.config.settings import settings


async def main() -> None:
    loader = MovieDataLoader()
    documents = loader.load_documents(settings.data.movie_plots_path)
    uploader = PineconeVectorStoreManager()
    await uploader.upload_documents(documents)

if __name__ == "__main__":
    asyncio.run(main())
