from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict, Iterable, List

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph

from src.agent.state import AgentState
from src.core.llm import get_llm
from src.tools.supabase_client import SupabaseResourceClient
from src.utils.resource_models import ResourceInput, ResourceRecord


CLASSIFICATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a classifier for a personal knowledge librarian agent.
Respond in JSON only. Do not add commentary.

If the user wants to save a resource (link, text, or both) set intent to
"store_resource" and extract:
- title: short descriptive title (string)
- url: http(s) link if present, otherwise null
- notes: any free-form notes
- tags: list of lowercase tags
- categories: list of broader categories (can be empty)

If the user wants to retrieve or search resources, set intent to
"fetch_resource" and extract:
- query: keywords or summary of what they want
- tags: list of tags mentioned
- categories: list of categories mentioned
- limit: number of items requested (default 5)

If you cannot determine intent, set intent to "chat".
""",
        ),
        ("user", "{user_input}"),
    ]
)


def classify_input(state: AgentState) -> Dict[str, Any]:
    """Use the LLM to determine whether to store or fetch resources."""

    user_message = state["messages"][-1]
    if not isinstance(user_message, HumanMessage):
        raise ValueError("Expected the latest message to be from the human user.")

    llm = get_llm()
    response = llm.invoke(
        CLASSIFICATION_PROMPT.format_messages(user_input=user_message.content)
    )

    parsed = _safe_json_parse(str(response.content))
    intent = _normalise_intent(parsed.get("intent"))

    return {
        "intent": intent,
        "parsed_request": parsed,
    }


def store_resource(state: AgentState) -> Dict[str, Any]:
    parsed = state.get("parsed_request", {}) or {}
    resource_data = parsed.get("resource") or parsed

    tags = _ensure_list(resource_data.get("tags"))
    categories = _ensure_list(resource_data.get("categories"))
    title = (resource_data.get("title") or "").strip()
    url = (resource_data.get("url") or "").strip() or None
    notes = (resource_data.get("notes") or "").strip() or None
    user_message_text = str(state["messages"][-1].content)

    if not title:
        title = _derive_title(url=url, fallback_text=user_message_text)

    if not notes and not url:
        notes = user_message_text

    payload = ResourceInput(
        title=title,
        url=url,
        notes=notes,
        tags=tags or None,
        categories=categories or None,
    )

    try:
        supabase = SupabaseResourceClient()
        record = supabase.add_resource(payload)
    except Exception as exc:
        return {
            "messages": [
                AIMessage(
                    content=(
                        "I couldn't save that resource because the Supabase API returned "
                        f"an error: {exc}"
                    )
                )
            ]
        }

    acknowledgement = _format_store_confirmation(record)

    return {
        "results": [_record_to_dict(record)],
        "messages": [AIMessage(content=acknowledgement)],
    }


def fetch_resources(state: AgentState) -> Dict[str, Any]:
    parsed = state.get("parsed_request", {}) or {}
    tags = _ensure_list(parsed.get("tags"))
    categories = _ensure_list(parsed.get("categories"))
    query = (parsed.get("query") or "").strip() or None
    limit = _coerce_limit(parsed.get("limit"))

    try:
        supabase = SupabaseResourceClient()
        records = supabase.fetch_resources(
            tags=tags or None,
            categories=categories or None,
            query=query,
            limit=limit,
        )
    except Exception as exc:
        return {
            "messages": [
                AIMessage(
                    content=(
                        "I couldn't look up your resources because the Supabase API returned "
                        f"an error: {exc}"
                    )
                )
            ]
        }

    message = _format_retrieval_response(
        records,
        tags=tags,
        categories=categories,
        query=query,
    )

    return {
        "results": [_record_to_dict(record) for record in records],
        "messages": [AIMessage(content=message)],
    }


def fallback_chat(state: AgentState) -> Dict[str, Any]:
    """Default to a plain chat response when no structured action is needed."""

    llm = get_llm()
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


def route_intent(state: AgentState) -> str:
    return state.get("intent") or "chat"


def build_graph():
    """Construct the LangGraph agent."""

    workflow = StateGraph(AgentState)

    workflow.add_node("classify", classify_input)
    workflow.add_node("store_resource", store_resource)
    workflow.add_node("fetch_resources", fetch_resources)
    workflow.add_node("chatbot", fallback_chat)

    workflow.add_edge(START, "classify")

    workflow.add_conditional_edges(
        "classify",
        route_intent,
        {
            "store_resource": "store_resource",
            "fetch_resource": "fetch_resources",
            "chat": "chatbot",
        },
    )

    workflow.add_edge("store_resource", END)
    workflow.add_edge("fetch_resources", END)
    workflow.add_edge("chatbot", END)

    return workflow.compile()


def _safe_json_parse(content: str) -> Dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                pass
    return {"intent": "chat"}


def _normalise_intent(intent: Any) -> str:
    if not isinstance(intent, str):
        return "chat"
    intent_lower = intent.lower().strip()
    if intent_lower in {"store", "save", "store_resource", "add"}:
        return "store_resource"
    if intent_lower in {"fetch", "retrieve", "search", "fetch_resource"}:
        return "fetch_resource"
    return "chat"


def _ensure_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        if not value.strip():
            return []
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _derive_title(*, url: str | None, fallback_text: str) -> str:
    if url:
        return url
    snippet = fallback_text.strip()
    if not snippet:
        return "Untitled resource"
    return snippet[:60] + ("…" if len(snippet) > 60 else "")


def _format_store_confirmation(record: ResourceRecord) -> str:
    parts = [f"Saved '{record.title}' to Notion."]
    if record.url:
        parts.append(f"Link: {record.url}")
    if record.tags:
        parts.append("Tags: " + ", ".join(record.tags))
    if record.categories:
        parts.append("Categories: " + ", ".join(record.categories))
    return "\n".join(parts)


def _format_retrieval_response(
    records: List[ResourceRecord],
    *,
    tags: List[str],
    categories: List[str],
    query: str | None,
) -> str:
    if not records:
        target = []
        if query:
            target.append(f"query '{query}'")
        if tags:
            target.append("tags " + ", ".join(tags))
        if categories:
            target.append("categories " + ", ".join(categories))
        descriptor = ", ".join(target) if target else "that request"
        return f"I couldn't find any saved resources for {descriptor}."

    lines = ["Here are the closest matches:"]
    for record in records:
        line = f"- {record.title}"
        if record.url:
            line += f" → {record.url}"
        metadata = []
        if record.tags:
            metadata.append("tags: " + ", ".join(record.tags))
        if record.categories:
            metadata.append("categories: " + ", ".join(record.categories))
        if metadata:
            line += " (" + "; ".join(metadata) + ")"
        lines.append(line)
    return "\n".join(lines)


def _record_to_dict(record: ResourceRecord) -> Dict[str, Any]:
    data = asdict(record)
    data["created_at"] = record.created_at.isoformat()
    return data


def _coerce_limit(value: Any) -> int:
    if isinstance(value, int) and value > 0:
        return min(value, 25)
    if isinstance(value, str) and value.strip().isdigit():
        return min(int(value.strip()), 25)
    return 5


# Singleton instance of the graph
graph = build_graph()
