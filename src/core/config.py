from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr

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
        extra="ignore" # Ignore extra env vars (like SYSTEM_*)
    )

    # Environment: dev or prod
    environment: Literal["dev", "prod"] = "dev"
    
    # --- LLM Settings ---
    # Provider selection: 'openai' or 'ollama'
    llm_provider: Literal["openai", "ollama"] = Field(
        default="ollama", 
        description="Which LLM provider to use."
    )
    
    # OpenAI (Optional if using Ollama, but good to type properly)
    openai_api_key: Optional[SecretStr] = Field(
        default=None, 
        description="Required if llm_provider is 'openai'"
    )
    
    # Ollama (Defaults to localhost)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # --- Database (Supabase) ---
    supabase_url: str = Field(..., description="Supabase Project URL")
    supabase_key: SecretStr = Field(..., description="Supabase API Key")

    # --- Integrations ---
    telegram_bot_token: Optional[SecretStr] = None

    def validate_llm_config(self):
        """Custom validation to ensure keys exist for chosen provider."""
        if self.llm_provider == "openai" and not self.openai_api_key:
            raise ValueError("LLM Provider is OpenAI, but OPENAI_API_KEY is missing!")

# Create a global settings object
settings = Settings()

# Validate immediately upon import
try:
    settings.validate_llm_config()
except ValueError as e:
    print(f"Configuration Error: {e}")
