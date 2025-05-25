from typing import TypedDict, List
from langchain_core.messages import BaseMessage

class MessagesState(TypedDict):
    messages: List[BaseMessage]
    next: str 