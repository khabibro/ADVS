from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "ADVS"
    database_url: str = "sqlite:///./advs_test.db"
    storage_path: Path = Path("./storage")
    max_upload_size_mb: int = 20
    max_pdf_pages: int = 30
    web_url: str = "http://localhost:3000"
    admin_url: str = "http://localhost:3002"
    api_url: str = "http://localhost:8000/api/v1"
    cors_origins: str = "http://localhost:3000,http://localhost:3002"
    ocr_provider: str = "paddle"
    paddle_ocr_device: str = "cpu"
    paddle_ocr_lang: str = "korean"
    paddle_ocr_rec_model_name: str = "korean_PP-OCRv5_mobile_rec"
    paddle_ocr_det_model_name: str = "PP-OCRv5_mobile_det"
    paddle_ocr_cache_dir: str = "./storage/paddleocr-cache"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def safe_log_context(self) -> dict[str, str | bool | int]:
        return {
            "app_env": self.app_env,
            "ocr_provider": self.ocr_provider,
            "max_upload_size_mb": self.max_upload_size_mb,
        }

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
