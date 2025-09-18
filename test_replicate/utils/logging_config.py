# mindx/utils/logging_config.py
import logging
import logging.handlers
import os
from pathlib import Path

# Use a default project root if the one from config isn't available yet
try:
    from .config import PROJECT_ROOT
except ImportError:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- Configuration ---
LOG_DIR = PROJECT_ROOT / "data" / "logs"
LOG_FILENAME = "mindx_runtime.log"
MAX_LOG_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5

_loggers = {}
_is_configured = False

# UPDATED: The function now accepts parameters for more flexible setup.
def setup_logging(
    log_level: str = "INFO", 
    console: bool = True, 
    log_file: bool = True
):
    """
    Configures the root logger for the MindX application.

    This function is idempotent and can be called multiple times without adverse effects.

    Args:
        log_level (str): The minimum logging level (e.g., "DEBUG", "INFO", "WARNING").
        console (bool): If True, logs will be output to the console.
        log_file (bool): If True, logs will be output to a rotating file.
    """
    global _is_configured
    if _is_configured:
        return

    # Convert string log level to logging constant
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers to prevent duplicate logs
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Define a standard formatter
    formatter = logging.Formatter(
        "[%(asctime)s] %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Configure Console Handler
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Configure File Handler
    if log_file:
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            log_path = LOG_DIR / LOG_FILENAME
            
            # Use RotatingFileHandler to manage log file size
            file_handler = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=MAX_LOG_SIZE_BYTES,
                backupCount=BACKUP_COUNT,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            # If file logging fails, log an error to the console (if available)
            # and continue without it.
            logging.basicConfig() # Basic config to ensure the next line prints
            logging.error(f"Failed to configure file logging at {LOG_DIR}: {e}", exc_info=True)

    _is_configured = True
    # Use the root logger to announce configuration status
    root_logger.info(f"Logging configured. Root level: {log_level}. Console: {console}. File: {log_file}.")

def get_logger(name: str) -> logging.Logger:
    """
    Retrieves a logger instance for a given module name.

    If logging has not been configured yet, it will trigger the default setup.
    """
    if not _is_configured:
        setup_logging() # Ensure default setup if not explicitly called

    if name in _loggers:
        return _loggers[name]
    
    logger = logging.getLogger(name)
    _loggers[name] = logger
    return logger
