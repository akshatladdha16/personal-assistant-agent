## Dependency Decisions
- **uv**: Rust-based package manager that locks Python version + dependencies (`uv.lock`) for reproducibility while keeping sync/install fast.
- **LangGraph**: Provides the state-machine abstraction required for looping over “classify → act → respond” cycles and later persistence via checkpointers.
- **notion-client**: Official Notion SDK used to create/query pages without re-implementing REST plumbing.
- **pydantic-settings**: Centralises configuration with type guarantees to surface missing credentials on startup.

## Architecture Decisions
- **Model factory (`src/core/llm.py`)**: One entry point for switching between local Ollama and cloud OpenAI models. Keeps the graph/tool nodes unaware of vendor details and enables caching.
- **Notion toolkit (`src/tools/notion_client.py`)**: Encapsulates page creation, query filtering, and parsing into a `ResourceRecord` dataclass. Keeps API specifics out of graph nodes.
- **Graph flow (`src/agent/graph.py`)**:
  1. *Classify*: LLM-only node that emits structured JSON (intent, payload).
  2. *Act*: Store or fetch nodes call Notion toolkit and craft human-readable feedback.
  3. *Fallback chat*: Falls back to plain LLM conversation when intent is unclear.
- **State schema (`src/agent/state.py`)**: Extends LangGraph state with `parsed_request`/`results` so each node can pass structured context forward without mutating shared globals.

## Operational Notes
- Run the agent with `uv run python -m src.main` so package imports resolve (now that `src/__init__.py` exists).
- `.env` requires Notion credentials; LLM provider remains configurable per environment.
- Future persistence layer will likely reuse LangGraph checkpointers (initial exploration will mirror data into Supabase or Notion).
