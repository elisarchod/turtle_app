from typing import List, Optional
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from langchain_community.document_loaders import CSVLoader
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Index, Pinecone, ServerlessSpec
import time

from turtleapp.settings import settings

logger = logging.getLogger(__name__)

class DocumentLoader:
    
    def load_documents(self, file_path: str, max_documents: Optional[int] = None) -> List[Document]:
        loader = CSVLoader(
            file_path=file_path,
            csv_args={
                'quotechar': '"',
                'fieldnames': ['release_year', 'title', 'director', 'cast', 'genre', 'plot']
            },
            content_columns=["title", "release_year", "director", "cast", "genre", "plot"]
        )
        documents = loader.load()
        
        if max_documents and len(documents) > max_documents:
            logger.info(f"Limiting documents from {len(documents)} to {max_documents}")
            documents = documents[:max_documents]
        
        return documents

class PineconeUploader:
    
    def __init__(
        self, 
        index_name: str = settings.pinecone.index_name, 
        embedding_model: str = settings.openai.embedding_model
    ) -> None:
        self.index_name = index_name
        self.embedding_model = embedding_model
        self.pinecone_api_key = settings.pinecone.api_key
        
        self.pc = Pinecone(api_key=self.pinecone_api_key)
        self._initialize_index()
        self.embeddings = OpenAIEmbeddings(model=self.embedding_model)
        self.vector_store = self._create_vector_store()

    def _initialize_index(self) -> None:
        existing_indexes = [index_info["name"] for index_info in self.pc.list_indexes()]
        
        if self.index_name not in existing_indexes:
            logger.info(f"Creating new index: {self.index_name}")
            self.pc.create_index(
                name=self.index_name,
                dimension=3072,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region=settings.pinecone.environment)
            )
            while not self.pc.describe_index(self.index_name).status["ready"]:
                time.sleep(1)
        
        self.pc_index = self.pc.Index(self.index_name)

    def _create_vector_store(self) -> PineconeVectorStore:
        return PineconeVectorStore(index=self.pc_index, embedding=self.embeddings)

    def generate_document_ids(self, documents: List[Document]) -> List[str]:
        return [f"movie_{i:05d}" for i in range(len(documents))]

    async def upload_documents(
        self, 
        documents: List[Document], 
        batch_size: int = 100, 
        max_workers: int = 4
    ) -> None:
        if not documents:
            logger.warning("No documents to upload")
            return
            
        document_ids = self.generate_document_ids(documents)
        total_documents = len(documents)
        
        logger.info(f"Uploading {total_documents} documents in batches of {batch_size}")
        
        batches = []
        for i in range(0, total_documents, batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_ids = document_ids[i:i + batch_size]
            batches.append((batch_docs, batch_ids))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self._upload_batch, batch_docs, batch_ids)
                for batch_docs, batch_ids in batches
            ]
            
            for i, future in enumerate(futures, 1):
                try:
                    future.result()
                    logger.info(f"Batch {i}/{len(batches)} uploaded")
                except Exception as e:
                    logger.error(f"Error uploading batch {i}: {e}")
                    raise
        
        logger.info("All documents uploaded successfully")

    def _upload_batch(self, documents: List[Document], document_ids: List[str]) -> None:
        self.vector_store.add_documents(documents=documents, ids=document_ids) 