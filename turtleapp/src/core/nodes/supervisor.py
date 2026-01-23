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
    """Creates a supervisor node that routes user requests to specialized agents.

    The supervisor analyzes incoming messages and decides which agent should handle
    the request, or if the conversation should end. This is the central routing
    component of the multi-agent system.
    """

    def __init__(self, llm: BaseChatModel, members: List[str]):
        """Initialize supervisor with routing LLM and available agents.

        Args:
            llm: Language model for routing decisions (typically Claude Sonnet)
            members: List of agent names available for routing. These names must
                    match the keys in the workflow's tools dictionary.
        """
        self.llm = llm
        self.members = members
        logger.info(f"Initializing SupervisorNodeCreator with members: {members}")
        
    def __call__(self, state: MessagesState) -> Command[Union[str]]:
        """Route user request to appropriate agent or end conversation.

        This is the core routing logic that:
        1. Examines the latest user message
        2. Uses the supervisor LLM with structured output to decide routing
        3. Returns a Command to transition to the chosen agent or END

        The LLM responds with {"next": "agent_name"} or {"next": "FINISH"}.
        "FINISH" is converted to LangGraph's END constant to terminate the workflow.

        Args:
            state: Current conversation state with message history

        Returns:
            Command with goto parameter specifying next node (agent name or END)
        """
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


