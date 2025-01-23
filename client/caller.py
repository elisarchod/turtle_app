"""
call the server using python
curl https://langchain-ai.github.io/assistants/search \
  --request POST \
  --header 'Content-Type: application/json' \
  --data '{
  "metadata": {},
  "graph_id": "",
  "limit": 10,
  "offset": 0
}'


"""
import requests
url_base = "https://langchain-ai.github.io/"
url_base = " http://127.0.0.1:2024"
url = f"{url_base}/assistants/search"

headers = {
    "Content-Type": "application/json"
}
data = {
    "metadata": {},
    "graph_id": "",
    "limit": 10,
    "offset": 0
}

response = requests.post(url, headers=headers, json=data)
print(response.json())

import requests
from dotenv import load_dotenv
from langgraph_sdk import get_client
from langgraph_sdk import get_sync_client

load_dotenv(override=True)
client = get_sync_client(url=os.environ["LANGSMITH_ENDPOINT"], api_key=os.environ["LANGCHAIN_API_KEY"])
client.assistants.search()



# example usage: client.<model>.<method_name>()
assistant = client.assistants.get(assistant_id="some_uuid")





LANGSMITH_API_KEY = os.environ["LANGCHAIN_API_KEY"]
# Set the headers
import requests


# Base URL of your LangSmith application
BASE_URL = "https://ht-frosty-battery-91-26df676ff73856d48624516684b654c1.us.langgraph.app"

# Example endpoint (replace with a real endpoint from the LangSmith API documentation)
ENDPOINT = "/runs"  # Example: Get a list of runs

# Construct the full URL
url = BASE_URL + ENDPOINT

# Set up the headers with the API key
headers = {
    "Authorization": f"Bearer {LANGSMITH_API_KEY}", "Content-Type": "application/json",
    # Often required for API requests
    }

# Example data to send (if it's a POST request) - modify as needed
data = {
    # "key": "value",  # Add relevant data for your specific request
    }

# Make the request (using GET as an example)
try:
    response = requests.get(url, headers=headers)
    # For POST requests:
    # response = requests.post(url, headers=headers, json=data)

    # Check for HTTP errors
    response.raise_for_status()

    # Process the response
    print(response.status_code)
    print(response.json())  # Assuming the response is JSON

except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")