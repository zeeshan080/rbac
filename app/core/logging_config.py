import logging
import sys
from app.core.config import settings # To potentially use settings for log level

# Ensure LOG_LEVEL is accessed correctly.
# Pydantic settings are generally available once the 'settings' instance is created.
# If this module is imported before 'settings' is fully initialized elsewhere (unlikely for FastAPI apps),
# it might be an issue. A common pattern is to configure logging inside a function called at startup.
# However, for basicConfig, it often needs to be at module level.
try:
    # Accessing settings.LOG_LEVEL might fail if settings model doesn't have it yet when this module is first imported.
    # This will be addressed when config.py is updated to include LOG_LEVEL.
    LOG_LEVEL_STR = settings.LOG_LEVEL.upper()
except AttributeError:
    # This fallback is if settings.LOG_LEVEL itself doesn't exist on the settings object.
    # If LOG_LEVEL exists but is None/empty, getattr below handles it.
    LOG_LEVEL_STR = "INFO"

# getattr will use logging.INFO if LOG_LEVEL_STR is not a valid level name (e.g. empty string)
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)

# Basic configuration sets up the root logger.
# If you need more sophisticated logging (e.g., different handlers, formatters per logger),
# use logging.config.dictConfig.
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(levelname)-8s - %(name)-25s - %(module)-15s - %(funcName)-20s - %(lineno)-5d - %(message)s", # More detailed format
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout, # Log to stdout, container orchestrators can pick this up.
)

def get_logger(name: str) -> logging.Logger:
    """Retrieves a logger instance with the specified name."""
    return logging.getLogger(name)

# Example: You might want to silence overly verbose loggers from libraries
# logging.getLogger("httpx").setLevel(logging.WARNING)
# logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
