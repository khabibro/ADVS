from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "ADVS"
    database_url: str = "sqlite:///./advs_test.db"
    storage_path: Path = Path("./storage")
    max_upload_size_mb: int = 20
    max_pdf_pages: int = Field(default=30, ge=1)
    # A4 at 288 DPI is about 8 MP. Allow up to ~3 such pages per image,
    # while bounding both skinny dimensions and total decoded RGB allocation.
    max_image_dimension: int = Field(default=16000, ge=1)
    max_image_pixels: int = Field(default=25_000_000, ge=1)
    max_pdf_render_pixels: int = Field(default=250_000_000, ge=1)
    max_ocr_temp_bytes: int = Field(default=100_000_000, ge=1)
    ocr_timeout_seconds: float = Field(default=120.0, gt=0)
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
    # PDF rasterization resolution for the OCR fallback path. 288 DPI (4x the
    # 72 DPI PDF point grid) rather than PaddleOCR's own 144 DPI default:
    # measured on a real 재학증명서, 144 DPI merged and mis-recognized the
    # letter-spaced document title so that "재학증명서" never appeared as a
    # contiguous substring, which alone forced classification to UNKNOWN.
    # 288 DPI recovered the title, reduced detected-box fragmentation
    # 36 -> 32, and raised mean line confidence 0.911 -> 0.933 at no
    # measurable latency cost. See evaluation/backend_audit/architecture_after.md.
    paddle_ocr_render_dpi: int = 288
    # Enable PaddleOCR's own orientation classifier. Rotation is a common
    # real-world capture condition and the current pipeline had no
    # orientation handling of any kind. Disabled by default only if the model
    # cannot be fetched; costs ~3 ms/page on CPU.
    paddle_ocr_doc_orientation: bool = True
    log_level: str = "INFO"
    # Auto-acceptance of OCR values (see document_intelligence/auto_acceptance.py).
    # S0 = off (every OCR field to a human) ... S6. Default on for Phase D.
    auto_accept_strategy: str = "S5"
    # Comma-separated workflow (checklist) ids for which auto-acceptance is switched off.
    auto_accept_disabled_workflows: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def _refuse_mock_ocr_in_production(self) -> "Settings":
        # The mock provider returns canned text; in production it would turn
        # every upload into a fabricated, plausible-looking document.
        if self.app_env.strip().lower() in {"production", "prod"} and (
            self.ocr_provider.strip().lower() == "mock"
        ):
            raise ValueError(
                "OCR_PROVIDER=mock is not allowed when APP_ENV is production; "
                "configure a real OCR provider (paddle)."
            )
        return self

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
    def auto_accept_disabled_workflow_ids(self) -> set[str]:
        return {
            item.strip() for item in self.auto_accept_disabled_workflows.split(",") if item.strip()
        }

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
