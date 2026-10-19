from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    data_dir: Path = PROJECT_ROOT / "data"
    textbooks_yaml: Path = BACKEND_DIR / "textbooks.yaml"
    ollama_base_url: str = "http://127.0.0.1:11434"
    chat_model: str = "qwen3.5:9b"
    embed_model: str = "nomic-embed-text"
    chroma_collection: str = "textbook_chunks"
    retrieve_k: int = 6


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
(settings.data_dir / "raw").mkdir(parents=True, exist_ok=True)
