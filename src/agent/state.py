from typing import Annotated, Any, List, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class BaseState(TypedDict):
    """Core state shared by every node."""

    messages: Annotated[List[BaseMessage], add_messages]


class AgentState(BaseState, total=False):
    """Extended state tracked across the workflow."""

    intent: Optional[str]
    parsed_request: dict[str, Any]
    results: List[dict[str, Any]]
