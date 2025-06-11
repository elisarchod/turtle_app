import os

from dotenv import load_dotenv

load_dotenv(override=True)

supervisor_model_name = os.environ["SUPERVISOR_MODEL"]
agent_model_name = os.environ["AGENT_MODEL"]
vector_db_index_name = os.environ["INDEX_NAME"]
vector_db_embedding_model_name = os.environ["EMBEDDINGS_MODEL"]

SERVER = os.getenv('SAMBA_SERVER')
SHARE = os.getenv('SAMBA_SHARE')
CREDENTIALS = {
    'user': os.getenv('SAMBA_USER'), 'password': os.getenv('SAMBA_PASSWORD')}