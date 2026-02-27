"""
QA Module - Logger

Logging utilities for QA module.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


class QALogger:
    """
    Logger for QA module operations.

    Provides structured logging for code generation,
    validation, and test execution.
    """

    _loggers = {}

    @classmethod
    def get_logger(cls, name: str = "lee.qa") -> logging.Logger:
        """
        Get or create a logger.

        Args:
            name: Logger name

        Returns:
            Logger instance
        """
        if name not in cls._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)

            # Console handler
            if not logger.handlers:
                console = logging.StreamHandler(sys.stdout)
                console.setLevel(logging.INFO)

                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                console.setFormatter(formatter)
                logger.addHandler(console)

            cls._loggers[name] = logger

        return cls._loggers[name]

    @classmethod
    def set_level(cls, level: int):
        """Set logging level for all QA loggers"""
        for logger in cls._loggers.values():
            logger.setLevel(level)

    @classmethod
    def add_file_handler(
        cls,
        log_file: Path,
        level: int = logging.DEBUG
    ):
        """
        Add file handler to all loggers.

        Args:
            log_file: Path to log file
            level: Logging level for file
        """
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        handler = logging.FileHandler(log_file)
        handler.setLevel(level)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)

        for logger in cls._loggers.values():
            logger.addHandler(handler)


def get_logger(name: str = "lee.qa") -> logging.Logger:
    """Convenience function to get logger"""
    return QALogger.get_logger(name)
