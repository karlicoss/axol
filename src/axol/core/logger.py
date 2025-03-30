import sys

from loguru import logger

fmt = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "{extra} | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)


def _add_exc_info(record) -> None:
    # loguru is a bit weird about exception logging
    # e.g. compare to import logging; logging.exception(o, exc_info=o)
    # see discussion here: https://github.com/Delgan/loguru/issues/1284
    if exception := record["extra"].get("exc_info"):
        record["exception"] = (type(exception), exception, exception.__traceback__)


config = {
    "handlers": [
        {"sink": sys.stderr, "format": fmt},
    ],
    "patcher": _add_exc_info,
}

logger.configure(**config)  # type: ignore[arg-type]
