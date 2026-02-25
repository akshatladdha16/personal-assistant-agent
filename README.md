# Resource Librarian Agent

An AI agent that captures every resource you share—links, notes, or mixed content—stores it in Supabase with structured tags/categories, and retrieves relevant items on demand. It is designed as a project-based learning exploration of LangGraph, tool-enabled LLMs, and local-first workflows (Ollama by default, OpenAI optional).

## What It Does
- Save new resources into a Supabase table with consistent columns (title, URL, notes, tags, categories).
- Update existing resources by re-saving them with new metadata (e.g., add a category later).
- Retrieve curated resource lists filtered by keywords or tags.
- Provide a simple CLI loop for experimenting with agent behaviour.

## Architecture Snapshot
| Layer | Purpose |
| --- | --- |
| `LangGraph` workflow | Intent classification → Supabase tool execution → response formatting |
| `SupabaseResourceClient` | Encapsulates inserts/queries against the `resources` table |
| `pydantic-settings` | Centralises environment configuration (LLM provider + Supabase credentials) |
| `uv` package manager | Reproducible dependency and Python version management |

## Getting Started

1. **Install dependencies**
   ```bash
   uv sync
   ```

2. **Prepare Supabase**
   - Create a table named `resources` (or choose your own name and update `SUPABASE_RESOURCES_TABLE`).
   - Recommended columns:
     - `id` UUID, default `uuid_generate_v4()`, primary key
     - `title` text (required)
     - `url` text (nullable)
     - `notes` text (nullable)
     - `tags` text (nullable) — store a single tag/keyword per resource
     - `categories` text (nullable) — store a single category per resource
     - `created_at` timestamptz, default `now()`
   - Create a Service Role key (or reuse the default) and note your project URL (`https://<project>.supabase.co`).

3. **Configure the agent**
   ```bash
   cp .env.example .env
   # Edit .env with:
   #   SUPABASE_URL=
   #   SUPABASE_KEY=
   # Optional: override table name with SUPABASE_RESOURCES_TABLE
   # Optional: switch LLM provider to openai and add OPENAI_API_KEY
   ```

4. **Run the CLI**
   ```bash
   uv run python -m src.main
   ```

   Example prompts:
   - `save https://arxiv.org/abs/1234 with tags ai, research`
   - `store “LangGraph lesson notes” under agent architectures`
- `find resources about prompt engineering tagged ai`

## Semantic Search with pgvector
- Enable the `pgvector` extension in Supabase and add an `embeddings_vector vector(1536)` column to the `resources` table.
- Apply the SQL in `supabase/match_resources.sql` (reproduced below) to register the RPC the agent calls (note the `drop function` to replace older versions safely):
  ```sql
  drop function if exists match_resources(vector, integer, double precision, text[], text[]);

  create function match_resources(
      query_embedding vector(1536),
      match_count integer default 10,
      match_threshold double precision default 1.0,
      filter_tags text[] default null,
      filter_categories text[] default null
  )
  returns table (
      id resources.id%TYPE,
      title resources.title%TYPE,
      url resources.url%TYPE,
      notes resources.notes%TYPE,
      tags resources.tags%TYPE,
      categories resources.categories%TYPE,
      created_at resources.created_at%TYPE
  )
  language plpgsql as $$
  begin
    return query
    select r.id, r.title, r.url, r.notes, r.tags, r.categories, r.created_at
    from resources r
    where r.embeddings_vector is not null
      and (filter_tags is null or r.tags = any(filter_tags))
      and (filter_categories is null or r.categories = any(filter_categories))
      and (r.embeddings_vector <=> query_embedding) <= match_threshold
    order by r.embeddings_vector <=> query_embedding
    limit match_count;
  end;
  $$;
  ```
- The default `match_threshold` of `1.0` effectively keeps the top matches without filtering; lower it (e.g., `0.4`) if you want to discard weaker similarities.
- Set `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, and `OPENAI_API_KEY` (or Ollama equivalents) in `.env`. The agent automatically generates embeddings on insert/update and falls back to keyword search if embedding fails.
- Backfill existing rows once after enabling embeddings:
  ```bash
  uv run python scripts/backfill_embeddings.py --batch-size 50
  ```

## Roadmap
- Conversation memory via LangGraph checkpointers (mirroring into Supabase)
- Automatic summaries for retrieved bundles
- Additional ingestion channels (email, RSS, read-it-later inboxes)

## Learn Alongside The Project
Development decisions and lessons learned are logged in `AI.md`. Each milestone explains the “why” behind the implementation to reinforce deliberate, project-based learning.
