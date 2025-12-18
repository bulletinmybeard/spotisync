import logging
from logging import Logger

from chalkbox import get_logger as chalkbox_get_logger, setup_logging as chalkbox_setup_logging


def get_logger(name: str) -> Logger:
    return chalkbox_get_logger(name)


def setup_logging() -> Logger:
    logger = chalkbox_setup_logging(
        level="WARNING",
        show_time=False,
        show_level=False,
        show_path=False,
        rich_tracebacks=False,
        json_file=None,
    )

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("spotipy").setLevel(logging.WARNING)

    return logger
