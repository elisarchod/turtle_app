import os

from dotenv import load_dotenv

load_dotenv(override=True)

supervisor_model_name = os.environ["SUPERVISOR_MODEL"]
agent_model_name = os.environ["AGENT_MODEL"]
vector_db_index_name = os.environ["INDEX_NAME"]
vector_db_embedding_model_name = os.environ["EMBEDDINGS_MODEL"]

SMB_SERVER_IP = os.getenv('SAMBA_SERVER')
SMB_SHARE_PATH = os.getenv('SAMBA_SHARE_PATH')
SMB_USERNAME = os.getenv('SAMBA_USER')
SMB_PASSWORD = os.getenv('SAMBA_PASSWORD')

# SAMBA_CREDENTIALS = {
#     'user': os.getenv('SAMBA_USER'),
#     'password': os.getenv('SAMBA_PASSWORD')}

QBITORRENT_IP_ADDRESS = os.getenv('QBITTORRENT_HOST')
QBITORRENT_CREDENTIALS = {
    'username': os.getenv('QBITTORRENT_USER'), 'password': os.getenv('QBITTORRENT_PASSWORD')}
