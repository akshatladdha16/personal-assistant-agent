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

## 5. Semantic Search Upgrade
**Goal:** Move beyond keyword `ilike` queries so retrieval understands context, not just literal matches.

### What Changed
- Added an `embeddings_vector` pgvector column and a `match_resources` Postgres function to Supabase so the database supports similarity search.
- Introduced `src/core/embeddings.py` to abstract embedding providers (OpenAI by default, Ollama optional) and plugged it into `SupabaseResourceClient` so inserts/updates automatically generate vectors.
- Updated the fetch path to blend semantic matches with the existing keyword fallback and respect tag/category filters.
- Documented setup steps (SQL function, backfill script, env vars) plus a batch backfill utility to populate historical rows.
- Added regression tests for the embedding helper utilities to guard against dimension mismatch and provider failures.
- Hardened the Supabase RPC by returning `%TYPE` columns and documenting a `drop function if exists` step so deployments can replace earlier signatures cleanly.
- Improved keyword fallback by normalising plural forms, searching URLs/tags/categories, and adding simple hyphen/space variants so queries like "ycombinator" and "startups" surface the expected saves even without embeddings.
- Raised the default semantic match threshold to `1.0` (no filtering) so vector search always returns the closest rows even when cosine distances are high; users can dial it down via config if they want stricter matches.

**Lesson:** Keeping Supabase as the single source of truth—storing both structured fields and vectors—simplifies operations while still unlocking contextual search. Clear fallbacks are essential so the agent stays useful even when embedding generation fails.

## 6. Next Learning Targets
- Persist conversation state / tool outputs with LangGraph checkpointers stored in Supabase.
- Add structured output validation (Pydantic) for the classifier to tighten robustness.
- Implement richer retrieval responses (LLM summarisation + grouping by tag/category).
- Build ingestion tests with a mocked Supabase client to validate payload construction without network calls.

---

## 7. Telegram DM Interface
**Goal:** Offer a mobile-friendly path to the agent while keeping access gated behind explicit approval.

### Implementation Notes
- Added `aiogram` as the async Telegram client and built `src/transport/telegram_bot.py`, which forwards DMs to the existing LangGraph workflow.
- Introduced a pairing policy inspired by OpenClaw’s DM guardrails: unknown users receive an 8-character code, pending requests expire after 1 hour, and only the configured `TELEGRAM_ADMIN_ID` can approve/reject.
- Created `src/pairing/store.py`, a JSON-backed store that tracks pending codes plus an allowlist. It enforces TTL, caps simultaneous requests, and exposes helpers for approval/revocation.
- Expanded configuration (`src/core/config.py`, `.env.example`, README) with Telegram settings so deployments can opt in without affecting the CLI path.
- The bot mirrors CLI outputs, including semantic-search warning notices, so messaging users see the same operational context as terminal users.

**Lesson:** Decoupling the transport layer from agent logic keeps LangGraph unchanged and lets us add messaging channels incrementally. A lightweight local pairing store delivers the “owner approval” workflow without a separate database, while still mirroring OpenClaw’s security ergonomics.
