import logging
import sys
import threading
from pathlib import Path
from datetime import datetime


class AppLogger:
    _loggers = {}
    _lock = threading.Lock()

    @classmethod
    def get_logger(cls, name: str, level: int = logging.INFO) -> logging.Logger:
        if name in cls._loggers:
            return cls._loggers[name]

        with cls._lock:
            if name in cls._loggers:
                return cls._loggers[name]

            logger = logging.getLogger(name)
            logger.setLevel(level)

            logger.handlers.clear()

            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)

            formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

            cls._loggers[name] = logger
            return logger

    @classmethod
    def set_level(cls, level: int):
        with cls._lock:
            for logger in cls._loggers.values():
                logger.setLevel(level)
                for handler in logger.handlers:
                    handler.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return AppLogger.get_logger(name)
