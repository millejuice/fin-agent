"""
Professional logging configuration.
"""
import logging
import sys
from typing import Optional

def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Set up application-wide logging with structured format.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    logger = logging.getLogger("fin_agent")
    logger.info(f"Logging initialized at {level} level")
    
    return logger

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance for a specific module."""
    logger_name = f"fin_agent.{name}" if name else "fin_agent"
    return logging.getLogger(logger_name)

