from typing import List, Optional
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import csv
from pathlib import Path
import time

from tqdm import tqdm

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

from turtleapp.settings import settings

logger = logging.getLogger(__name__)

MAX_DOCUMENTS = 300
METADATA_DELIMITER = " | "

class MovieDataLoader:
    
    def load_documents(self, file_path: str) -> List[Document]:
        documents = []
        
        with Path(file_path).open(encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for i, row in enumerate(tqdm(reader, desc="Loading documents", total=MAX_DOCUMENTS)):
                if i >= MAX_DOCUMENTS:
                    break
                    
                formatted_content = self._format_movie_data(row)
                doc = Document(page_content=formatted_content)
                documents.append(doc)
                
        return documents
    
    def _format_movie_data(self, row: dict[str, str]) -> str:
        fields = []
        
        for field_name in ['title', 'release_year', 'director', 'cast', 'genre', 'plot']:
            if value := row.get(field_name, '').strip():
                fields.append(f"{field_name}: {value}")
            
        return METADATA_DELIMITER.join(fields)

class PineconeVectorStoreManager:
    
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
            
            for i, future in enumerate(tqdm(futures, desc="Uploading batches", unit="batch"), 1):
                try:
                    future.result()
                    logger.info(f"Batch {i}/{len(batches)} uploaded")
                except Exception as e:
                    logger.error(f"Error uploading batch {i}: {e}")
                    raise
        
        logger.info("All documents uploaded successfully")

    def _upload_batch(self, documents: List[Document], document_ids: List[str]) -> None:
        self.vector_store.add_documents(documents=documents, ids=document_ids) 