from typing import List
import logging
from pathlib import Path
from uuid import uuid4

from langchain_community.document_loaders import CSVLoader
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Index, Pinecone, ServerlessSpec
import time

from ..config import (
    PINECONE_API_KEY,
    PINECONE_INDEX_NAME,
    OPENAI_EMBEDDING_MODEL,
    PROCESSED_DATA_DIR
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PineconeUploader:
    def __init__(self, index_name: str = PINECONE_INDEX_NAME, embedding_model: str = OPENAI_EMBEDDING_MODEL):
        self.index_name = index_name
        self.embedding_model = embedding_model
        self.pinecone_api_key = PINECONE_API_KEY
        
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
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
            while not self.pc.describe_index(self.index_name).status["ready"]:
                time.sleep(1)
        self.pc_index: Index = self.pc.Index(self.index_name)

    def _create_vector_store(self) -> PineconeVectorStore:
        return PineconeVectorStore(index=self.pc_index, embedding=self.embeddings)

    def load_documents(self, file_path: str) -> List[Document]:
        try:
            loader = CSVLoader(
                file_path=file_path,
                csv_args={
                    'quotechar': '"',
                    'fieldnames': ['release_year', 'title', 'genre', 'plot']
                },
                content_columns=["title", "release_year", "genre", "plot"]
            )
            return loader.load()[1:]
        except Exception as e:
            logger.error(f"Error loading documents: {str(e)}")
            raise

    def generate_document_ids(self, documents: List[Document]) -> List[str]:
        formatted_ids = []
        for i, doc in enumerate(documents):
            num = i + 1
            title_raw = doc.page_content.split("\n")[1].replace("title: ", "")
            formatted_ids.append(f'mp{num:05d}_{title_raw}'.replace(' ', ""))
        return formatted_ids

    def upload_documents(self, documents: List[Document]) -> None:
        try:
            document_ids = self.generate_document_ids(documents)
            logger.info(f"Uploading {len(documents)} documents to Pinecone")
            self.vector_store.add_documents(documents=documents, ids=document_ids)
            logger.info("Documents uploaded successfully")
        except Exception as e:
            logger.error(f"Error uploading documents: {str(e)}")
            raise

def main():
    try:
        uploader = PineconeUploader()
        documents = uploader.load_documents(PROCESSED_DATA_DIR / "plot_summaries_sample.csv")
        uploader.upload_documents(documents)
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        raise

if __name__ == "__main__":
    main()


