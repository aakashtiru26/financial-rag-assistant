from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Enterprise Financial RAG Assistant"
    environment: str = "local"
    api_key: str = Field(default="change-me", min_length=1)

    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "llama3.2:1b"
    ollama_embedding_model: str = "nomic-embed-text"

    groq_api_key: str = ""
    openai_api_key: str = ""
    huggingface_api_token: str = ""

    data_dir: Path = Path("./data")
    upload_dir: Path = Path("./data/uploads")
    index_dir: Path = Path("./data/index")
    metadata_dir: Path = Path("./data/metadata")

    chunk_size: int = Field(default=1200, ge=200)
    chunk_overlap: int = Field(default=180, ge=0)
    retrieval_k: int = Field(default=5, ge=1, le=20)
    max_upload_mb: int = Field(default=50, ge=1, le=500)
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_prefix="FIN_RAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def metadata_file(self) -> Path:
        return self.metadata_dir / "documents.json"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
