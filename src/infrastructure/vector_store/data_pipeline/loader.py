import csv
from pathlib import Path

from tqdm import tqdm

from langchain_core.documents import Document

MAX_DOCUMENTS = 3000
METADATA_DELIMITER = " | "


class MovieDataLoader:

    def load_documents(self, file_path: str) -> list[Document]:
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
