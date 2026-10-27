import logging
from logging.handlers import RotatingFileHandler

from zero_semester.config import get_settings


def configure_logging(service_name: str) -> None:
    settings = get_settings()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(console)
    try:
        settings.log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            settings.log_dir / f"{service_name}.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
    except OSError:
        root.warning("Persistent log directory %s is unavailable", settings.log_dir)
    else:
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        framework_logger = logging.getLogger(logger_name)
        framework_logger.handlers.clear()
        framework_logger.propagate = True
