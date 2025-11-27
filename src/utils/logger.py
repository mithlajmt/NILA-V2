# src/utils/logger.py
import logging
import logging.handlers
from pathlib import Path
import sys

def setup_logger(log_level: str = "INFO", log_file: str = "data/logs/robot.log"):
    """Setup application logging with Windows compatibility"""
    
    # Create logs directory
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging with UTF-8 encoding
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # Console handler with UTF-8 encoding
            logging.StreamHandler(sys.stdout),
            # File handler with UTF-8 encoding
            logging.FileHandler(
                log_file,
                encoding='utf-8'  # ← ADD THIS FOR EMOJI SUPPORT
            )
        ]
    )
    
    # Set third-party library log levels
    logging.getLogger("pygame").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)