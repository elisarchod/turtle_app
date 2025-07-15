import asyncio
from turtleapp.data_pipeline.vector_store.uploader import DocumentLoader, PineconeUploader
from turtleapp.settings import settings

async def main() -> None:
    loader = DocumentLoader()
    documents = loader.load_documents(settings.data.movie_plots_path)
    doc = documents[1]
    uploader = PineconeUploader()
    await uploader.upload_documents(documents)

if __name__ == "__main__":
    asyncio.run(main())