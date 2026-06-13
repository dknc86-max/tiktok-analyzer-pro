"""
Logging configuration for TikTok Analyzer Pro.
Provides consistent logging across all modules.
"""

import logging
import logging.handlers
from pathlib import Path
from config import LOG_LEVEL, LOG_FILE

# Create logs directory if it doesn't exist
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Create logger
logger = logging.getLogger("tiktok_analyzer")
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

# Create formatters
detailed_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
simple_formatter = logging.Formatter(
    "%(levelname)s: %(message)s",
)

# File handler (detailed)
file_handler = logging.handlers.RotatingFileHandler(
    LOG_DIR / LOG_FILE,
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
)
file_handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
file_handler.setFormatter(detailed_formatter)

# Console handler (simpler)
console_handler = logging.StreamHandler()
console_handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
console_handler.setFormatter(simple_formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(f"tiktok_analyzer.{name}")
