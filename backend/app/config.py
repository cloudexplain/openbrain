import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Azure OpenAI Configuration
    azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_openai_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2023-12-01-preview")
    azure_openai_deployment_name: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")
    azure_openai_embedding_deployment_name: str = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")
    
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