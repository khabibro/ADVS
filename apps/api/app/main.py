import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.document_intelligence.ocr.warmup import warm_up_ocr

settings = get_settings()
configure_logging(settings.log_level)



@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    warmup = asyncio.create_task(warm_up_ocr(settings)) if settings.ocr_warmup else None
    yield
    if warmup is not None and not warmup.done():
        warmup.cancel()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api/v1")


@app.get("/health")
def root_health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(Exception)
async def unhandled_exception(_: Request, exc: Exception) -> JSONResponse:
    if settings.app_env == "production":
        return JSONResponse(
            status_code=500,
            content={"detail": {"code": "INTERNAL_ERROR", "message": "Internal server error"}},
        )
    return JSONResponse(
        status_code=500, content={"detail": {"code": "INTERNAL_ERROR", "message": str(exc)}}
    )
