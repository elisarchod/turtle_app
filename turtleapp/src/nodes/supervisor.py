from typing import List, TypedDict, Union

from langchain import hub
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.constants import END
from langgraph.graph import MessagesState
from langgraph.types import Command

from dotenv import load_dotenv

load_dotenv(override=True)

hub_prompt: ChatPromptTemplate = hub.pull("supervisor_prompt_with_placeholder")

class Router(TypedDict):
    """Worker to route to next. If no workers needed, route to FINISH."""
    next: Union[str]


class SupervisorNodeCreator:
    def __init__(self, llm: BaseChatModel, members: List[str]):
        self.llm = llm
        self.members = members
    def __call__(self, state: MessagesState) -> Command[Union[str]]:
        """An LLM-based router."""
        message_with_prompt = hub_prompt.invoke({"human_request": state["messages"],
                                                 "members": self.members})

        response = self.llm.with_structured_output(Router).invoke(message_with_prompt)
        goto = response["next"]
        if goto == "FINISH": goto = END
        return Command(goto=goto)


if __name__ == '__main__':
    members = ["worker1", "worker2", "worker3"]
    state={'messages': [HumanMessage(content='recommend 3 comedy movies',
                                     additional_kwargs={},
                                     response_metadata={},
                                     id='123')]}

    def get_supervisor_system_prompt(members: List[str]) -> str:
        return (
            f"You are a supervisor tasked with managing a conversation between the following workers: {members}. "
            f"Given the following user request, respond with the worker to act next. "
            f"Each worker will perform a task and respond with their results and status. When finished, respond with FINISH.")
    system_prompt = get_supervisor_system_prompt(members)
    messages = [{"role": "system", "content": system_prompt}, ] + state["messages"]
    response2 = ChatOpenAI(temperature=0, model="gpt-4-0125-preview").with_structured_output(Router).invoke(messages)
