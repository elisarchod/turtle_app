###### load data
# import pandas as pd
# df = pd.read_csv("create_vector_db/wiki_movie_plots_deduped.csv")
# df.columns = [col.lower().replace(" ", "_").replace("/", "_") for col in df.columns]
# df_sampled = df.query("release_year ==2017 & origin_ethnicity == 'American'").sample(200, random_state=1)[['release_year', 'title', 'genre', 'plot']]
# df_sampled.to_csv('create_vector_db/plot_summaries_sample.csv', index=False)
from typing import List
from uuid import uuid4

###### create embedings
from langchain_community.document_loaders import CSVLoader, TextLoader
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from openai import embeddings
from pinecone import Index, Pinecone, ServerlessSpec
import os
import time
from dotenv import load_dotenv
load_dotenv(override=True)
# with open("create_vector_db/plot_summaries_sample.csv", "r") as f:
#     print(f.read())
INDEX_NAME = "movie-recommender-sample-200"
EMBEDDING_MODEL = "text-embedding-3-large"

loader = CSVLoader(file_path="create_vector_db/plot_summaries_sample.csv",
                   csv_args={'quotechar': '"',
                            'fieldnames': ['release_year', 'title', 'genre', 'plot']},
                   content_columns = ["title", "release_year", "genre", "plot"]
                   )
documents: List[Document] = loader.load()[1:]
pinecone_api_key = os.environ.get("PINECONE_API_KEY")
pc = Pinecone(api_key=pinecone_api_key)

#### find existing indexes
existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
if INDEX_NAME not in existing_indexes:
    pc.create_index(name=INDEX_NAME, dimension=3072, metric="cosine", spec=ServerlessSpec(cloud="aws", region="us-east-1"), )
    while not pc.describe_index(INDEX_NAME).status["ready"]:
        time.sleep(1)


#### create embeddings
pc_index: Index = pc.Index(INDEX_NAME)
embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
vector_store = PineconeVectorStore(index=pc_index, embedding=embeddings)

# uuids = [str(uuid4())[:8] for _ in range(len(documents))]
import re
formated_ids = []
for i in range(len(documents)):
    num = i + 1
    title_raw = documents[i].page_content.split("\n")[1].replace("title: ", "")
    # title = re.sub(r"[^a-zA-Z0-9]", "", title_raw)
    # year = str(documents[i].page_content["release_year"])
    formated_ids.append(f'mp{num:05d}_{title_raw}'.replace(' ', ""))
documents[i].page_content

pp = documents[0]
documents[0].page_content.split("\n")[1].replace("title: ", "")
# vector_store.add_documents(documents=documents, ids=formated_ids)


