from typing import List, TypedDict, Union

from langchain import hub
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langgraph.constants import END
from langgraph.graph import MessagesState
from langgraph.types import Command

from turtleapp.src.utils import logger

hub_prompt: ChatPromptTemplate = hub.pull("supervisor_prompt_with_placeholder")

class Router(TypedDict):
    next: Union[str]

class SupervisorNodeCreator:
    def __init__(self, llm: BaseChatModel, members: List[str]):
        self.llm = llm
        self.members = members
        logger.info(f"Initializing SupervisorNodeCreator with members: {members}")
        
    def __call__(self, state: MessagesState) -> Command[Union[str]]:
        logger.info("Supervisor processing request")
        message_with_prompt = hub_prompt.invoke({
            "question": state["messages"],
            "members": self.members
        })

        response = self.llm.with_structured_output(Router).invoke(message_with_prompt)
        goto = response["next"]
        if goto == "FINISH": 
            goto = END
            logger.info("Supervisor routing to END")
        else:
            logger.info(f"Supervisor routing to: {goto}")
        return Command(goto=goto)


