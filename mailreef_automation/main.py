"""
Main entry point for the email automation system
Run this to start the automation
"""

import logging
import time
import sys
import os

# Add project root to path BEFORE any other imports
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

# Debug: List root dir to see if automation_scrapers is there
print(f"DEBUG: ROOT_DIR is {ROOT_DIR}")
try:
    print(f"DEBUG: Root contents: {os.listdir(ROOT_DIR)}")
    scrapers_path = os.path.join(ROOT_DIR, 'automation_scrapers')
    if os.path.exists(scrapers_path):
        print(f"DEBUG: automation_scrapers dir exists. Contents: {os.listdir(scrapers_path)}")
    else:
        print(f"DEBUG: automation_scrapers dir NOT FOUND at {scrapers_path}")
except Exception as e:
    print(f"DEBUG: Error listing dir: {e}")

import automation_config
from mailreef_client import MailreefClient
from scheduler import EmailScheduler
from contact_manager import ContactManager
from monitor import DeliverabilityMonitor
from logger_util import get_logger
import lock_util

# Configure logging
logger = get_logger("SYSTEM_MAIN")

def main():
    """Initialize and start the email automation"""
    # Safety first: Ensure only one instance runs
    lock_util.ensure_singleton('sender')
    
    try:
        logger.info("Initializing Mailreef Email Automation System")
        
        class ConfigWrapper:
            pass
        
        cfg = ConfigWrapper()
        # Loading attributes from automation_config module to cfg object
        for name in dir(automation_config):
            if not name.startswith("__"):
                setattr(cfg, name, getattr(automation_config, name))
                
        # Check API key
        if not cfg.MAILREEF_API_KEY:
            logger.error("MAILREEF_API_KEY environment variable not set.")
            return

        # 🔍 Run Network Diagnostics (Cloud Debugging)
        try:
            from diagnose_network import run_diagnostics
            run_diagnostics()
        except ImportError:
            logger.warning("diagnose_network.py not found, skipping network check.")
        except Exception as e:
            logger.error(f"Error running diagnostics: {e}")
        
        mailreef = MailreefClient(
            api_key=cfg.MAILREEF_API_KEY,
            base_url=cfg.MAILREEF_API_BASE
        )
        
        # Cloud-First: We don't use SQLite anymore.
        # db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "campaign.db")
        # contacts = ContactManager(database_path=db_path)
        
        # Check for stale locks from previous crashes (Leaving this as it might be used by lock_util for process locks, but not db locks)
        # logger.info("Audit: Checking for stale lead locks...")
        # contacts.scan_stale_locks()
        
        # Init Scheduler with Sheets
        try:
            scheduler = EmailScheduler(
                mailreef_client=mailreef,
                # contact_manager=contacts, # Removed
                config=cfg
            )
        except Exception as e:
            logger.critical(f"Failed to initialize scheduler (likely Sheets Auth error): {e}")
            return
        
        monitor = DeliverabilityMonitor(mailreef, cfg)
        
        # Validate setup
        logger.info("Validating inbox configuration...")
        try:
            inboxes = mailreef.get_inboxes()
            
            if len(inboxes) < cfg.TOTAL_INBOXES:
                logger.warning(f"Expected {cfg.TOTAL_INBOXES} inboxes, found {len(inboxes)}")
            
            # Check inbox health
            logger.info("Checking inbox health...")
            for inbox in inboxes:
                try:
                    # Optimized to avoid 95 API calls on startup if not strictly necessary,
                    # but following the prompt's structure:
                    status = mailreef.get_inbox_status(inbox["id"])
                    if status.get("deliverability_score", 100) < 80:
                        logger.warning(f"Inbox {inbox['id']} has low deliverability: {status}")
                except Exception as e:
                    logger.warning(f"Could not check status for inbox {inbox['id']}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to fetch inboxes: {e}")
            # Depending on severity, might exit or continue
        
        # Start the scheduler
        logger.info("Starting email scheduler...")
        scheduler.start()
        
        # Start monitoring
        logger.info("Starting deliverability monitoring...")
        monitor.start()
        
        # Start Reply Watcher (Background Thread)
        logger.info("Starting reply watcher...")
        from reply_watcher import ReplyWatcher
        watcher = ReplyWatcher()
        import threading
        watcher_thread = threading.Thread(target=watcher.run_daemon, daemon=True)
        watcher_thread.start()
        
        logger.info("Email automation system is now running (Sheets-First Mode)")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Critical System Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if 'scheduler' in locals(): scheduler.stop()
        if 'monitor' in locals(): monitor.stop()
        lock_util.release_lock('sender')
        lock_util.release_lock('watcher')

if __name__ == "__main__":
    main()
