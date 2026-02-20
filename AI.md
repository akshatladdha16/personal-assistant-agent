# AI Agent Development Log

Project-based learning notes for building a Supabase-backed resource librarian agent with LangGraph. Each section captures the goals, design decisions, and lessons from each milestone so future iterations stay intentional.

## 1. Foundation & Setup
**Goal:** Establish a production-ready Python project template.

### Key Decisions
- **`uv`** keeps dependency management fast and reproducible via `uv.lock`.
- **`pydantic-settings`** provides typed configuration in `src/core/config.py`, highlighting missing environment variables early.
- **Model factory** (`src/core/llm.py`) abstracts LLM providers (Ollama ↔ OpenAI) behind a cached `get_llm()` helper.

**Lesson:** Centralising config and model selection keeps downstream modules pure and easy to test.

---

## 2. Pivot: Supabase Resource Librarian
**Goal:** Focus the assistant on storing and retrieving learning resources using Supabase as the source of truth.

### Changes Introduced
- Swapped the Notion dependency for the official Supabase Python SDK.
- Reworked configuration to require `SUPABASE_URL` and `SUPABASE_KEY`, with optional table overrides.
- Defined a canonical `resources` table schema (text fields + text[] arrays for tags/categories).

**Lesson:** Relational storage with SQL filtering supports richer queries (array `contains`, `ilike`) while keeping the setup approachable for project-based learning.

---

## 3. Supabase Integration Toolkit
**Goal:** Encapsulate database access in reusable helpers.

### Implementation Notes
- `src/utils/resource_models.py` holds `ResourceInput`/`ResourceRecord` dataclasses and utility functions for normalising lists and parsing timestamps.
- `src/tools/supabase_client.py` lets the agent upsert resources: if a title/URL already exists we patch only the supplied fields; otherwise we insert a new row.
- Tags and categories are stored as simple `text` columns—MVP constraint is “one tag/category per resource”—so filters rely on keyword `ilike` matching.

**Lesson:** Converting DB rows into rich Python objects keeps graph nodes simple and easier to reason about.

---

## 4. LangGraph Workflow v1
**Goal:** Route user input to the right Supabase action.

### Flow
1. **Classify (`classify_input`)** – LLM-only node that emits structured JSON (intent, resource data, filters).
2. **Act (`store_resource` / `fetch_resources`)** – Calls the Supabase toolkit, transforms results, and crafts deterministic confirmations.
3. **Fallback (`chatbot`)** – Falls back to a plain chat response when the intent is unclear.

### Supporting Changes
- `src/agent/state.py` extends the state TypedDict with optional `parsed_request` and `results` fields.
- `src/main.py` now guides the user through saving/finding resources and wraps agent execution in helpful error handling.

**Lesson:** Keeping the LLM responsible for *decision + extraction* while deterministic Python performs the action yields predictable side effects.

---

## 5. Next Learning Targets
- Persist conversation state / tool outputs with LangGraph checkpointers stored in Supabase.
- Add structured output validation (Pydantic) for the classifier to tighten robustness.
- Implement richer retrieval responses (LLM summarisation + grouping by tag/category).
- Build ingestion tests with a mocked Supabase client to validate payload construction without network calls.
