import logging
import re

from pythonjsonlogger import jsonlogger

_TOKEN_QUERY = re.compile(r"([?&]token=)[^&\s\"']+")


class RedactTokens(logging.Filter):
    """Remove ?token=... query values from access-log records (the submission link secret)."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _TOKEN_QUERY.sub(r"\1[redacted]", record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(
                _TOKEN_QUERY.sub(r"\1[redacted]", a) if isinstance(a, str) else a
                for a in record.args
            )
        return True


def _json_handler() -> logging.Handler:
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)
    return handler


def configure_logging(level: str = "INFO") -> None:
    for name in ("uvicorn.access", "uvicorn", "httpx"):
        logging.getLogger(name).addFilter(RedactTokens())
    handler = _json_handler()
    app_logger = logging.getLogger("app")
    app_logger.handlers.clear()
    app_logger.addHandler(handler)
    app_logger.setLevel(level)
    app_logger.propagate = False

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(_json_handler())
    root.setLevel(level)
