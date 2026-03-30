"""ToolAgent class for ReAct-based specialized agents."""

from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_core.tools import Tool
from langgraph.graph import MessagesState
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from core.constants import SUPERVISOR_NODE
from infrastructure.llm.factory import create_agent_llm
from application.agents.prompts import AGENT_BASE_PROMPT


class ToolAgent:
    """Specialized ReAct agent that uses specific tools to complete tasks."""

    def __init__(
        self,
        tools: list[Tool],
        name: str | None = None,
        specialized_prompt: str | None = None,
    ) -> None:
        self.tools = tools
        self.name = name or f"{tools[0].name}_agent"
        self.llm = create_agent_llm()
        prompt = specialized_prompt or AGENT_BASE_PROMPT

        self.agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=prompt,
        )

    def process(self, state: MessagesState) -> Command[Literal["supervisor"]]:
        """Execute agent task and return control to supervisor."""
        if not state["messages"]:
            return Command(
                update={"messages": [HumanMessage(content="No message provided")]},
                goto=SUPERVISOR_NODE,
            )

        latest_message = state["messages"][-1].content
        result = self.agent.invoke({"messages": [HumanMessage(content=latest_message)]})
        output = result["messages"][-1].content

        return Command(
            update={"messages": [HumanMessage(content=output)]},
            goto=SUPERVISOR_NODE,
        )
