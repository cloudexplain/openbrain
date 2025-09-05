import os
from typing import List
from pydantic_settings import BaseSettings


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
    azure_openai_embedding_deployment_name: str = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "")

    # Ollama Configuration
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "smollm2:135m")
    ollama_embedding_model: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

    api_v1_str: str = "/api/v1"

    # Database Configuration
    database_url: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://secondbrain:password@localhost:5432/secondbrain"
    )

    # CORS Configuration (allow comma-separated env var)
    cors_origins: List[str] = os.getenv("CORS_ORIGINS", "*")
    def __init__(self, **values):
        super().__init__(**values)
        if isinstance(self.cors_origins, str):
            self.cors_origins = [s.strip() for s in self.cors_origins.split(",") if s.strip()]


settings = Settings()