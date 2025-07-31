from typing import List, TypedDict, Union

from langchain_core.language_models import BaseChatModel
from langgraph.constants import END
from langgraph.graph import MessagesState
from langgraph.types import Command

from turtleapp.src.core.prompts import SUPERVISOR_PROMPT
from turtleapp.src.utils import logger

class Router(TypedDict):
    next: Union[str]

class SupervisorNodeCreator:
    def __init__(self, llm: BaseChatModel, members: List[str]):
        self.llm = llm
        self.members = members
        logger.info(f"Initializing SupervisorNodeCreator with members: {members}")
        
    def __call__(self, state: MessagesState) -> Command[Union[str]]:
        logger.info("Supervisor processing request")
        latest_message = state["messages"][-1].content
        
        message_with_prompt = SUPERVISOR_PROMPT.invoke({
            "question": latest_message
        })

        response = self.llm.with_structured_output(Router).invoke(message_with_prompt)
        goto = response["next"]
        if goto == "FINISH": 
            goto = END
            logger.info("Supervisor routing to END")
        else:
            logger.info(f"Supervisor routing to: {goto}")
        return Command(goto=goto)


