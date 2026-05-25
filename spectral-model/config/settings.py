from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    anthropic_api_key: str = Field("", env="ANTHROPIC_API_KEY")
    tavily_api_key: str = Field("", env="TAVILY_API_KEY")
    serpapi_api_key: str = Field("", env="SERPAPI_API_KEY")
    stack_exchange_api_key: str = Field("", env="STACK_EXCHANGE_API_KEY")

    log_level: str = Field("INFO", env="LOG_LEVEL")
    max_concurrent_requests: int = Field(5, env="MAX_CONCURRENT_REQUESTS")
    quality_score_threshold: float = Field(0.7, env="QUALITY_SCORE_THRESHOLD")

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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
