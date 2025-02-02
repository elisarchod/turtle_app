# import os
# import requests
# from langgraph_sdk import get_client
# from langgraph_sdk import get_sync_client
#
#
# from dotenv import load_dotenv
# load_dotenv(override=True)
#
# # set the LANGSMITH_API_KEY environment variable (create key in settings)
# from langchain import hub
#
# hub.pull("supervisor_prompt_with_placeholder")
# # LANGSMITH_ENDPOINT=https://ht-frosty-battery-91-26df676ff73856d48624516684b654c1.us.langgraph.app
#
# client = get_sync_client(url=os.environ["LANGSMITH_ENDPOINT"], api_key=os.environ["LANGCHAIN_API_KEY"])
# graph_name = "home_recommender"
# assistant_id = "8d1135ad-00f6-5552-af4f-35a99dc143b8"
# assistant = client.assistants.get(assistant_id=assistant_id)
#
# response = client.ask(assistant_id=graph_name,
#                       query="bla bla bla",
#                       thread_id=1111)  # Include thread_id if needed
#
#
#
# client.runs.list_runs(project_name=graph_name, execution_order=1, error=False)
# client.runs.list(thread_id=1)
# runs = client.runs.list(
#     project_name=graph_name,
#     # start_time=start_time,
#     # end_time=end_time,
#     execution_order=1,
#     # Top-level runs only
#     error=False,
#     # Successful runs only
#     )
#
# assistant = client.assistants.get(graph_name)
#
#
# client.runs.create(assistant_id=graph_name, thread_id="thread_456",
#                    input={"message": "bla bla"},)
#
#
#
#
# # --- 3. Process Runs and Calculate Metrics ---
# latencies = []
# for run in runs:
#     if run.end_time and run.start_time:
#         latency = (run.end_time - run.start_time).total_seconds()
#         latencies.append(latency)
#
# # --- 4. Analyze and Answer the Question ---
# if latencies:
#     average_latency = sum(latencies) / len(latencies)
#     print(f"Question: {question}")
#     print(f"Answer: The average latency over the last 24 hours for successful runs is: {average_latency:.2f} seconds")
# else:
#     print(f"Question: {question}")
#     print("Answer: No successful runs found in the specified time range.")
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
# client.assistants.get_graph(assistant_id="home_recommender")
#
# client.threads.create(assistant_id="home_recommender", data={"metadata": {
#     "configurable": {"thread_id": "gen_int_13"}}})
#
# client.threads.create()
#
#
# config = {"configurable": {"thread_id": "gen_int_13"}}  # , "run_name": "gen_numbers_test_01"
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
# assistant =  client.assistants.create(graph_id="agent",
#     config={"configurable": {"model_name": "openai"}},
#     metadata={"number": 1},
#     assistant_id="home_recommender",
#     if_exists="do_nothing",
#     name="my_name")
#
#
#
# # result: AddableValuesDict = agent.invoke({
# #                                              "messages": "tell me the plot of terminator 2 ?"}, )  # config=config,
# # result['messages'][-1].pretty_print()
# # """
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
# # example usage: client.<model>.<method_name>()
# assistant = client.assistants.get(assistant_id="some_uuid")
#
#
#
#
#
# LANGSMITH_API_KEY = os.environ["LANGCHAIN_API_KEY"]
# # Set the headers
# import requests
#
#
# # Base URL of your LangSmith application
# BASE_URL = "https://ht-frosty-battery-91-26df676ff73856d48624516684b654c1.us.langgraph.app"
#
# # Example endpoint (replace with a real endpoint from the LangSmith API documentation)
# ENDPOINT = "/runs"  # Example: Get a list of runs
#
# # Construct the full URL
# url = BASE_URL + ENDPOINT
#
# # Set up the headers with the API key
# headers = {
#     "Authorization": f"Bearer {LANGSMITH_API_KEY}", "Content-Type": "application/json",
#     # Often required for API requests
#     }
#
# # Example data to send (if it's a POST request) - modify as needed
# data = {
#     # "key": "value",  # Add relevant data for your specific request
#     }
#
# # Make the request (using GET as an example)
# try:
#     response = requests.get(url, headers=headers)
#     # For POST requests:
#     # response = requests.post(url, headers=headers, json=data)
#
#     # Check for HTTP errors
#     response.raise_for_status()
#
#     # Process the response
#     print(response.status_code)
#     print(response.json())  # Assuming the response is JSON
#
# except requests.exceptions.RequestException as e:
#     print(f"An error occurred: {e}")