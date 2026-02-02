import logging
import os
from datetime import datetime
from pathlib import Path

# Base directory for logs
LOGS_DIR = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "automation.log"

def get_logger(name: str):
    """Returns a pre-configured logger with obsessive formatting."""
    logger = logging.getLogger(name)
    
    # If logger already has handlers, don't add more (prevents duplicate logs)
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.DEBUG)
    
    # Obsessive Formatting
    # Example: 2026-02-03 10:00:00 | SCHEDULER | INFO | Found 12 leads
    formatter = logging.Formatter(
        '%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console Handler (for real-time terminal viewing)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # File Handler (for tail -f automation.log)
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # 3. Telegram Handler (Critical Alerts)
    # Check if TELEGRAM_AVAILABLE and configured
    try:
        # Avoid circular import if possible, but safe here inside function or try-except top level
        # We'll use dynamic import to be safe
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from telegram_alert import TelegramNotifier, TelegramLogHandler
        
        notifier = TelegramNotifier()
        if notifier.token and notifier.chat_id:
            tg_handler = TelegramLogHandler(notifier)
            tg_handler.setLevel(logging.ERROR) # Alert on ERROR and CRITICAL
            tg_handler.setFormatter(formatter)
            logger.addHandler(tg_handler)
    except Exception as e:
        # Don't crash logging if telegram fails setup
        print(f"Failed to add Telegram handler: {e}")
    
    return logger
