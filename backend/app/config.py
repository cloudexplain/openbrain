import os

from typing import List, Union, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App meta
    project_name: str = os.getenv("PROJECT_NAME", "SecondBrain")

    # LLM Provider Selection
    llm_provider: str = os.getenv("LLM_PROVIDER", "azure_openai")  # "azure_openai" oder "ollama"

    # Azure OpenAI Configuration
    azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_openai_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2023-12-01-preview")
    azure_openai_deployment_name: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")
    azure_mini_deployment_name: str = os.getenv("AZURE_MINI_DEPLOYMENT_NAME", "gpt-4o-mini")
    azure_openai_embedding_deployment_name: str = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "text-embedding-3-small")

    # Ollama Configuration
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "smollm2:135m")
    ollama_embedding_model: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")


    embedding_model: Optional[str] = None
    embedding_dim: Optional[int] = None
    # Security Configuration
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    search_api_key: str = os.getenv("SEARCH_API_KEY", "your-search-api-key-here")

    api_v1_str: str = "/api/v1"

    # Database Configuration
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://secondbrain:password@localhost:5432/secondbrain"
    )

    # CORS Configuration (allow comma-separated env var)
    cors_origins: List[str] = ["*"]

    @field_validator("cors_origins", mode="before")
    def validate_cors_origins(cls, v):
        """
        Akzeptiert:
         - "*" (Wildcard) -> ["*"]
         - Komma-separierte Strings: "https://a.com,https://b.com"
         - JSON-Array-Strings: '["https://a.com"]'
         - bereits Listen
        """
        # Wenn nichts gesetzt, versuche die Umgebungsvariable
        if v is None or v == ["*"]:
            env_value = os.getenv("CORS_ORIGINS", None)
            if env_value is None:
                return ["*"]
            v = env_value

        # jetzt v kann ein String oder eine Liste sein
        if isinstance(v, str):
            s = v.strip()
            if s == "*" or s == '["*"]':
                return ["*"]
            # JSON-Array-String?
            if s.startswith("[") and s.endswith("]"):
                try:
                    import json
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        return parsed
                except Exception:
                    pass
            # Komma-separierter String
            return [part.strip() for part in s.split(",") if part.strip()]

        # bereits eine Liste
        return v
    
    @property
    def embedding_model_resolved(self) -> str:
        """
        Rückgabe des tatsächlich zu verwendenden Embedding-Modells:
        1) explicit EMBEDDING_MODEL env var / override
        2) provider-spezifischer Default (ollama vs azure)
        """
        if self.embedding_model:
            return self.embedding_model
        if self.llm_provider == "ollama":
            return self.ollama_embedding_model
        # Azure-Feld heißt azure_openai_embedding_deployment_name
        return self.azure_openai_embedding_deployment_name


def get_settings() -> Settings:
    """Get settings instance - lazy loaded when needed."""
    return Settings()

# Global settings instance
settings = get_settings()
