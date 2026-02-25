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

## Roadmap
- Conversation memory via LangGraph checkpointers (mirroring into Supabase)
- Automatic summaries for retrieved bundles
- Additional ingestion channels (email, RSS, read-it-later inboxes)

## WhatsApp Bridge (Local Prototype)
1. **Configure environment**
   - Copy `.env.example` to `.env` and add `WPPCONNECT_SESSION`, `WPPCONNECT_TOKEN`, and (optionally) `WPPCONNECT_WEBHOOK_SECRET` after generating a token from the WPPConnect server.
2. **Start WPPConnect locally**
   - Copy `wppconnect.config.example.json` to `wppconnect.config.json`, update the webhook URL if needed, and run:
     ```bash
     npx @wppconnect/server@latest --config ./wppconnect.config.json
     ```
   - Scan the QR code in the terminal with the WhatsApp account that should act as the agent.
3. **Run the FastAPI bridge**
   ```bash
   uv run python -m src.whatsapp_server
   ```
   The server listens on `0.0.0.0:8080` by default and forwards incoming WhatsApp messages into the LangGraph agent.
4. **(Optional) Expose the bridge**
   - When you need WhatsApp webhooks to reach your machine from outside your network, open a tunnel such as:
     ```bash
     npx localtunnel --port 8080 --subdomain resource-librarian
     ```
   - Update `webhook.url` in `wppconnect.config.json` to the tunnel URL.

## Learn Alongside The Project
Development decisions and lessons learned are logged in `AI.md`. Each milestone explains the “why” behind the implementation to reinforce deliberate, project-based learning.
