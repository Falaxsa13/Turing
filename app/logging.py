import sys
from loguru import logger
from app.config import settings


def setup_logging():
    """Configure loguru logging"""
    # Remove default handler
    logger.remove()

    # Add console handler with appropriate level based on environment
    log_level = "DEBUG" if settings.app_env == "dev" else "INFO"

    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
    )

    # Add file handler for production
    if settings.app_env != "dev":
        logger.add(
            "logs/app.log",
            rotation="500 MB",
            retention="10 days",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        )

    logger.info(f"Logging setup complete for environment: {settings.app_env}")
