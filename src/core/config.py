from typing import Literal, Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings.

    This class loads variables from the environment (or .env file).
    Pydantic automatically validates types and missing values.
    """

    # --- Core Settings ---
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra env vars (like SYSTEM_*)
    )

    # Environment: dev or prod
    environment: Literal["dev", "prod"] = "dev"

    # --- LLM Settings ---
    # Provider selection: 'openai' or 'ollama'
    llm_provider: Literal["openai", "ollama"] = Field(
        default="ollama", description="Which LLM provider to use."
    )

    # OpenAI (Optional if using Ollama, but good to type properly)
    openai_api_key: Optional[SecretStr] = Field(
        default=None, description="Required if llm_provider is 'openai'"
    )

    # Ollama (Defaults to localhost)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # --- Supabase ---
    supabase_url: str = Field(
        ..., description="Supabase project URL (https://<project>.supabase.co)"
    )
    supabase_key: SecretStr = Field(
        ..., description="Supabase service role or anon key with table access"
    )
    supabase_resources_table: str = Field(
        default="resources",
        description="Table used to store resource rows",
    )

    # --- WhatsApp Transport ---
    wppconnect_base_url: str = Field(
        default="http://localhost:21465",
        description="Base URL for the WPPConnect server",
    )
    wppconnect_session: Optional[str] = Field(
        default=None,
        description="Name of the WPPConnect session to control",
    )
    wppconnect_token: Optional[SecretStr] = Field(
        default=None,
        description="Bearer token used to call the WPPConnect REST API",
    )
    wppconnect_webhook_secret: Optional[SecretStr] = Field(
        default=None,
        description="Optional shared secret expected in webhook requests",
    )

    # --- Embeddings ---
    embedding_provider: Literal["openai", "ollama", "none"] = Field(
        default="openai",
        description="Embedding backend used for semantic search",
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model identifier",
    )
    embedding_dimensions: int = Field(
        default=1536,
        description="Expected dimensionality for stored embeddings",
    )
    embedding_match_threshold: float = Field(
        default=1.0,
        description="Cosine distance threshold for semantic matches (1.0 for no filtering)",
    )

    def validate_llm_config(self):
        """Custom validation to ensure keys exist for chosen provider."""
        if self.llm_provider == "openai" and not self.openai_api_key:
            raise ValueError("LLM Provider is OpenAI, but OPENAI_API_KEY is missing!")

    def validate_supabase_config(self):
        """Ensure Supabase credentials are present."""
        if not self.supabase_url:
            raise ValueError("SUPABASE_URL is required for resource management.")
        if not self.supabase_key:
            raise ValueError("SUPABASE_KEY is required for resource management.")


# Create a global settings object
settings = Settings()

# Validate immediately upon import
try:
    settings.validate_llm_config()
    settings.validate_supabase_config()
except ValueError as e:
    print(f"Configuration Error: {e}")
