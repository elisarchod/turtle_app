"https://langchain-ai.github.io/langgraph/how-tos/react-agent-from-scratch/?h=create+agent+react#define-nodes-and-edges"

from typing import Literal
from langgraph.graph.message import MessagesState

import json
from langchain_core.messages import ToolMessage, SystemMessage
from langchain_core.runnables import RunnableConfig


from langchain_openai import ChatOpenAI
from langgraph.types import Command

from app.src.tools.random_number_gen import rand_gen

model = ChatOpenAI(model="gpt-4o-mini")



tools = [rand_gen]
model = model.bind_tools(tools)
tools_by_name = {tool.name: tool for tool in tools}

tool_call = {
     "name": "generate_random_floats",
    "args": {"min_number": 0.1, "max_number": 3.3333, "array_size": 3},
    "id": "123",  # required
    "type": "tool_call",  # required
    }



def tool_node(state: MessagesState):
    outputs = []
    for tool_call in state["messages"][-1].tool_calls:
        tool_i = tools_by_name[tool_call["name"]]
        tool_result = tool_i.invoke(tool_call["args"])
        outputs.append(ToolMessage(content=json.dumps(tool_result),
                                   name=tool_call["name"],
                                   tool_call_id=tool_call["id"], ))
    return {"messages": outputs}


# Define the node that calls the model
def call_model(state: MessagesState, config: RunnableConfig, ) -> Command[Literal["supervisor"]]:
    # this is similar to customizing the create_react_agent with state_modifier, but is a lot more flexible
    system_prompt = SystemMessage("You are a helpful AI assistant, please respond to the users query to the best of your ability!")
    response = model.invoke([system_prompt] + state["messages"], config)
    # We return a list, because this will get added to the existing list
    return {"messages": [response]}


########################


# def coder_node(state: MessagesState) -> Command[Literal["supervisor"]]:
#     research_agent: CompiledGraph = create_react_agent(llm,
#                                                        tools=[rand_gen],
#                                                        state_modifier=rand_gen.description)
#     research_agent.name = "python_functions"
#     last_message = research_agent.invoke(state)["messages"][-1]
#     return Command(update={
#         "messages": [HumanMessage(content=last_message.content,
#                                   # additional_kwargs={'array':last_message.artifact}
#                                   )]},
#         goto="supervisor", )
