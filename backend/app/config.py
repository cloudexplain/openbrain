import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Azure OpenAI Configuration
    azure_openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_api_version: str = "2023-12-01-preview"
    azure_openai_deployment_name: str = "gpt-4"
    azure_openai_embedding_deployment_name: str = "text-embedding-ada-002"
    
    # Database Configuration
    database_url: str
    
    # CORS Configuration - use str to avoid JSON parsing issues
    cors_origins_raw: str = "*"
    
    # API Configuration
    api_v1_str: str = "/api/v1"
    project_name: str = "SecondBrain API"
    
    # Security Configuration
    secret_key: str
    
    # Azure Email Configuration (Optional)
    azure_email_connection_string: str = ""
    azure_email_sender_address: str = ""
    
    # Frontend URL Configuration
    base_url: str = "http://localhost:5173"
    
    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        if self.cors_origins_raw == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins_raw.split(',') if origin.strip()]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra='ignore',  # Ignore extra fields like POSTGRES_USER, etc.
        env_ignore_empty=True,  # Ignore empty env vars
        # Read CORS_ORIGINS as cors_origins_raw
        fields={'cors_origins_raw': {'env': 'CORS_ORIGINS'}}
    )


def get_settings() -> Settings:
    """Get settings instance - lazy loaded when needed."""
    return Settings()