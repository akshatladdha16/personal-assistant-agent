## Dependency Decisions
- **uv**: Rust-based package manager that locks Python version + dependencies (`uv.lock`) for reproducibility while keeping sync/install fast.
- **LangGraph**: Provides the state-machine abstraction required for looping over “classify → act → respond” cycles and later persistence via checkpointers.
- **supabase**: Official Supabase Python SDK handles PostgREST queries for storing and retrieving resources.
- **pydantic-settings**: Centralises configuration with type guarantees to surface missing credentials on startup.

## Architecture Decisions
- **Model factory (`src/core/llm.py`)**: One entry point for switching between local Ollama and cloud OpenAI models. Keeps the graph/tool nodes unaware of vendor details and enables caching.
- **Supabase toolkit (`src/tools/supabase_client.py`)**: Encapsulates inserts/queries and maps rows to a `ResourceRecord` dataclass. Keeps API specifics out of graph nodes.
- **Graph flow (`src/agent/graph.py`)**:
  1. *Classify*: LLM-only node that emits structured JSON (intent, payload).
  2. *Act*: Store or fetch nodes call the Supabase toolkit and craft human-readable feedback.
  3. *Fallback chat*: Falls back to plain LLM conversation when intent is unclear.
- **State schema (`src/agent/state.py`)**: Extends LangGraph state with `parsed_request`/`results` so each node can pass structured context forward without mutating shared globals.

## Operational Notes
- Run the agent with `uv run python -m src.main` so package imports resolve (now that `src/__init__.py` exists).
- `.env` requires Supabase credentials (`SUPABASE_URL`, `SUPABASE_KEY`); LLM provider remains configurable per environment.
- Supabase table schema stores `tags` and `categories` as simple `text` columns; the agent currently supports one tag/category per resource and uses `ilike` filters for retrieval.
