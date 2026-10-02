import logging

from pythonjsonlogger import jsonlogger


def _json_handler() -> logging.Handler:
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)
    return handler


def configure_logging(level: str = "INFO") -> None:
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
