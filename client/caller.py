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
