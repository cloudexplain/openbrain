import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM Provider Selection
    llm_provider: str = os.getenv("LLM_PROVIDER", "azure_openai")  # "azure_openai" oder "ollama"
    
    # Azure OpenAI Configuration
    azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_openai_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2023-12-01-preview")
    azure_openai_deployment_name: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")
    azure_openai_embedding_deployment_name: str = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")

    # Ollama Configuration
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "smollm2:135m")
    ollama_embedding_model: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

    # Database Configuration
    database_url: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://secondbrain:password@localhost:5432/secondbrain"
    )
    
    # CORS Configuration
    cors_origins: List[str] = os.getenv("CORS_ORIGINS",
        [
         "*",
         # "http://localhost:3000",
         # "http://localhost:5173",
         # "http://localhost:4173",
        ])
    if isinstance(cors_origins, str):
        cors_origins = cors_origins.split(",")
    # API Configuration
    api_v1_str: str = "/api/v1"
    project_name: str = "SecondBrain API"
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()