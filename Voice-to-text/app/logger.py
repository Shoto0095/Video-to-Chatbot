import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime


class NoiseFilter(logging.Filter):
    """Filter to exclude noisy third-party logs."""
    
    EXCLUDED_LOGGERS = {
        "watchfiles.main",
        "watchfiles",
        "uvicorn.access",
        "httpx",
        "httpcore",
    }
    
    def filter(self, record):
        # Exclude logs from noisy loggers
        return record.name not in self.EXCLUDED_LOGGERS


def configure_logging(level: int = logging.INFO):
    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Create log filename with current date
    log_filename = logs_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    
    # Create formatters
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # File handler with daily rotation
    file_handler = TimedRotatingFileHandler(
        filename=log_filename,
        when="midnight",
        interval=1,
        backupCount=30,  # Keep logs for 30 days
        encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y-%m-%d.log"
    
    # Add noise filter to file handler
    file_handler.addFilter(NoiseFilter())
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Add file handler only (no console output)
    root_logger.addHandler(file_handler)
    
    # Set higher log levels for noisy third-party loggers
    logging.getLogger("watchfiles").setLevel(logging.ERROR)
    logging.getLogger("watchfiles.main").setLevel(logging.ERROR)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.ERROR)
    logging.getLogger("httpx").setLevel(logging.ERROR)
    logging.getLogger("httpcore").setLevel(logging.ERROR)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("langchain_core").setLevel(logging.WARNING)
    logging.getLogger("langchain_google_genai").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)


def get_logger(name: str):
    configure_logging()
    return logging.getLogger(name)
