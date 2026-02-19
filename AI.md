# AI Agent Development Log

Project-based learning notes for building a Notion-backed resource librarian agent with LangGraph. Each section captures the goals, design decisions, and lessons from each milestone so future iterations stay intentional.

## 1. Foundation & Setup
**Goal:** Establish a production-ready Python project template.

### Key Decisions
- **`uv`** keeps dependency management fast and reproducible via `uv.lock`.
- **`pydantic-settings`** provides typed configuration in `src/core/config.py`, highlighting missing environment variables early.
- **Model factory** (`src/core/llm.py`) abstracts LLM providers (Ollama ↔ OpenAI) behind a cached `get_llm()` helper.

**Lesson:** Centralising config and model selection keeps downstream modules pure and easy to test.

---

## 2. Pivot: Notion Resource Librarian
**Goal:** Narrow the assistant’s scope to storing and retrieving learning resources from Notion.

### Changes Introduced
- Replaced Supabase/Gmail ambitions with a focused Notion workflow.
- Simplified `.env` to require Notion credentials (`NOTION_API_KEY`, `NOTION_RESOURCE_DATABASE_ID`).
- Added `notion-client` dependency via `uv` and removed unused integrations.

**Lesson:** Tight, outcome-driven scope (capture → organise → retrieve) accelerates learning compared to diffuse “assistant” ambitions.

---

## 3. Notion Integration Toolkit
**Goal:** Encapsulate Notion API access in reusable helpers.

### Implementation Notes
- `src/utils/notion_format.py` defines property constants and a `ResourceRecord` dataclass, and handles property/record translation.
- `src/tools/notion_client.py` wraps the official SDK with `add_resource` and `fetch_resources` methods, plus basic filtering (tags, categories, keyword search).
- Error handling surfaces API issues cleanly to the agent nodes.

**Lesson:** Converting API payloads into rich Python objects keeps graph nodes simple and easier to reason about.

---

## 4. LangGraph Workflow v1
**Goal:** Route user input to the right Notion action.

### Flow
1. **Classify (`classify_input`)** – LLM-only node that emits structured JSON (intent, resource data, filters).
2. **Act (`store_resource` / `fetch_resources`)** – Calls the Notion toolkit, transforms results, and crafts deterministic confirmations.
3. **Fallback (`chatbot`)** – Falls back to a plain chat response when the intent is unclear.

### Supporting Changes
- `src/agent/state.py` extends the state TypedDict with optional `parsed_request` and `results` fields.
- `src/main.py` now guides the user through saving/finding resources and wraps agent execution in helpful error handling.

**Lesson:** Keeping the LLM responsible for *decision + extraction* while deterministic Python performs the action yields predictable side effects.

---

## 5. Next Learning Targets
- Persist conversation state / tool outputs with LangGraph checkpointers (Supabase or Notion mirrors).
- Add structured output validation (Pydantic) for the classifier to tighten robustness.
- Implement richer retrieval responses (LLM summarisation + grouping by tag/category).
- Build ingestion tests with a mocked Notion client to validate payload construction.
