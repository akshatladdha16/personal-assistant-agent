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

    # --- Notion ---
    notion_api_key: Optional[SecretStr] = Field(
        default=None,
        description="Internal integration token with access to the workspace",
    )
    notion_resource_database_id: Optional[str] = Field(
        default=None, description="Notion database ID where resources are stored"
    )
    notion_default_parent_page_id: Optional[str] = Field(
        default=None,
        description="Optional parent page ID to scope new databases or pages",
    )

    def validate_llm_config(self):
        """Custom validation to ensure keys exist for chosen provider."""
        if self.llm_provider == "openai" and not self.openai_api_key:
            raise ValueError("LLM Provider is OpenAI, but OPENAI_API_KEY is missing!")

    def validate_notion_config(self):
        """Ensure Notion credentials look present."""
        if not self.notion_api_key:
            raise ValueError("NOTION_API_KEY is required for resource management.")
        if not self.notion_resource_database_id:
            raise ValueError(
                "NOTION_RESOURCE_DATABASE_ID is required for resource management."
            )


# Create a global settings object
settings = Settings()

# Validate immediately upon import
try:
    settings.validate_llm_config()
    settings.validate_notion_config()
except ValueError as e:
    print(f"Configuration Error: {e}")
