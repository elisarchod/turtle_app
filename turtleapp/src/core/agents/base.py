from typing import Any, Dict, List
from langchain_core.messages import BaseMessage
from langchain_core.language_models import BaseChatModel

class BaseAgent:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    def process(self, messages: List[BaseMessage]) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement process method") 