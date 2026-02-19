# Resource Librarian Agent

An AI agent that captures every resource you share—links, notes, or mixed content—stores it in Notion with structured tags/categories, and retrieves relevant items on demand. It is designed as a project-based learning exploration of LangGraph, tool-enabled LLMs, and local-first workflows (Ollama by default, OpenAI optional).

## What It Does
- Save new resources into a Notion database with consistent properties (title, URL, notes, tags, categories).
- Retrieve curated resource lists filtered by keywords or tags.
- Provide a simple CLI loop for experimenting with agent behaviour.

## Architecture Snapshot
| Layer | Purpose |
| --- | --- |
| `LangGraph` workflow | Intent classification → Notion tool execution → response formatting |
| `notion-client` wrapper | Encapsulates page creation and database queries |
| `pydantic-settings` | Centralises environment configuration (LLM provider + Notion credentials) |
| `uv` package manager | Reproducible dependency and Python version management |

## Getting Started

1. **Install dependencies**
   ```bash
   uv sync
   ```

2. **Prepare Notion**
   - Create a database with the following properties (all title/multi-select types): `Title`, `URL`, `Notes`, `Tags`, `Categories`.
   - Create an internal integration and share the database with it.
   - Copy the database ID and the integration token.

3. **Configure the agent**
   ```bash
   cp .env.example .env
   # Edit .env with:
   #   NOTION_API_KEY=
   #   NOTION_RESOURCE_DATABASE_ID=
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
- Conversation memory + Supabase/Notion checkpointing
- Automatic summaries for retrieved bundles
- Additional ingestion channels (email, RSS, read-it-later inboxes)

## Learn Alongside The Project
Development decisions and lessons learned are logged in `AI.md`. Each milestone explains the “why” behind the implementation to reinforce deliberate, project-based learning.
