from typing import Any, Dict, List
from langchain_core.messages import BaseMessage
from langchain_core.language_models import BaseChatModel

from turtleapp.src.utils import logger

class BaseAgent:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        logger.info(f"Initializing BaseAgent with LLM: {type(llm).__name__}")

    def process(self, messages: List[BaseMessage]) -> Dict[str, Any]:
        logger.info("BaseAgent process method called - should be overridden by subclasses")
        raise NotImplementedError("Subclasses must implement process method") 