from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # watsonx.ai
    watsonx_api_key: str
    watsonx_project_id: str
    watsonx_url: str = "https://eu-de.ml.cloud.ibm.com"

    # Granite Models (single model for all tasks)
    granite_chat_model: str = "ibm/granite-4-h-small"
    granite_embedding_model: str = "ibm/granite-embedding-278m-multilingual"

    # Cloudant
    cloudant_api_key: str
    cloudant_url: str
    cloudant_database: str = "startup-funding"

    # App
    app_env: str = "development"
    app_port: int = 8000
    chroma_persist_dir: str = "./chroma_gemini"
    log_level: str = "INFO"
    gemini_api_key: str | None = None
    use_mock_ai: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
