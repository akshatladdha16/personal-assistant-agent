## Dependency Decisions
- **uv**: Rust-based package manager that locks Python version + dependencies (`uv.lock`) for reproducibility while keeping sync/install fast.
- **LangGraph**: Provides the state-machine abstraction required for looping over “classify → act → respond” cycles and later persistence via checkpointers.
- **supabase**: Official Supabase Python SDK handles PostgREST queries for storing and retrieving resources.
- **pydantic-settings**: Centralises configuration with type guarantees to surface missing credentials on startup.

## Architecture Decisions
- **Model factory (`src/core/llm.py`)**: One entry point for switching between local Ollama and cloud OpenAI models. Keeps the graph/tool nodes unaware of vendor details and enables caching.
- **Embedding service (`src/core/embeddings.py`)**: Wraps embedding providers (OpenAI, Ollama, or disabled) behind a cached helper so persistence code can request vectors without vendor coupling.
- **Supabase toolkit (`src/tools/supabase_client.py`)**: Encapsulates inserts/queries, now handles embedding generation + storage (`embeddings_vector`) and blends semantic search (via `match_resources` RPC) with an expanded keyword fallback (singular/plural variants, URL/tag/category matches). Keeps API specifics out of graph nodes.
- **Graph flow (`src/agent/graph.py`)**:
  1. *Classify*: LLM-only node that emits structured JSON (intent, payload).
  2. *Act*: Store or fetch nodes call the Supabase toolkit and craft human-readable feedback.
  3. *Fallback chat*: Falls back to plain LLM conversation when intent is unclear.
- **State schema (`src/agent/state.py`)**: Extends LangGraph state with `parsed_request`/`results` so each node can pass structured context forward without mutating shared globals.

## Operational Notes
- Run the agent with `uv run python -m src.main` so package imports resolve (now that `src/__init__.py` exists).
- `.env` requires Supabase credentials (`SUPABASE_URL`, `SUPABASE_KEY`) plus embedding config (`EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, etc.) when semantic search is enabled.
- Supabase schema now includes an `embeddings_vector vector(1536)` column and a `match_resources` RPC (see `supabase/match_resources.sql`, which uses `%TYPE` so the function matches your column types automatically and drops any previous definition before creating the new one). Tags and categories remain single-text fields; semantic + keyword filters (with plural handling) are combined in the client. Default `match_threshold` is `1.0` (no filtering) so we always get top-K results; tune via env if you need tighter matches.
