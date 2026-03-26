import logging
import sys
from datetime import datetime

def setup_logger(name: str = "SautiYetu", level: int = logging.INFO) -> logging.Logger:
    """
    Simple drop-in logger setup for the application.
    
    Args:
        name: Logger name (default: "SautiYetu")
        level: Logging level (default: logging.INFO)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Console handler with formatted output
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

# Create default logger instance
logger = setup_logger()