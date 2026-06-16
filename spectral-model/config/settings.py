from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str = ""
    tavily_api_key: str = ""
    serpapi_api_key: str = ""
    stack_exchange_api_key: str = ""

    log_level: str = "INFO"
    max_concurrent_requests: int = 5
    quality_score_threshold: float = 0.7

    claude_model: str = "claude-sonnet-4-5"
    max_retries: int = 5
    base_retry_delay: float = 1.0

    data_dir: Path = Path("./data")
    raw_dir: Path = Path("./data/raw")
    processed_dir: Path = Path("./data/processed")
    rejected_dir: Path = Path("./data/rejected")
    intermediate_dir: Path = Path("./data/intermediate")
    db_path: Path = Path("./data/spectral_iam.db")
    chroma_path: Path = Path("./data/chroma")

    dedup_threshold: float = 0.92
    dedup_model: str = "all-MiniLM-L6-v2"

    min_output_length: int = 100
    max_output_length: int = 4000


settings = Settings()
