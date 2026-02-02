import os
import sys
import logging

logger = logging.getLogger("LOCK_UTIL")

def ensure_singleton(process_name: str):
    """
    Ensure only one instance of the process is running using a PID file.
    process_name: 'sender' or 'watcher'
    """
    pid_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(pid_dir, exist_ok=True)
    
    pid_file = os.path.join(pid_dir, f"{process_name}.pid")
    pid = str(os.getpid())

    if os.path.isfile(pid_file):
        try:
            with open(pid_file, 'r') as f:
                old_pid = int(f.read().strip())
                
            # Check if process with old_pid is actually running
            os.kill(old_pid, 0)
            
            # If no error, process is running
            print(f"❌ CRITICAL ERROR: Another instance of {process_name} is already running (PID: {old_pid}).")
            print(f"If you are sure it's not running, delete {pid_file} and try again.")
            logger.critical(f"Aborting start: {process_name} already running with PID {old_pid}")
            sys.exit(1)
        except (OSError, ValueError, ProcessLookupError):
            # Process is not running, we can take over the lock
            pass

    # Write current PID to lock file
    with open(pid_file, 'w') as f:
        f.write(pid)
    
    logger.info(f"🔒 Locked {process_name} with PID {pid}")

def release_lock(process_name: str):
    """Release the lock file on exit."""
    pid_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    pid_file = os.path.join(pid_dir, f"{process_name}.pid")
    if os.path.isfile(pid_file):
        try:
            os.remove(pid_file)
            logger.info(f"🔓 Released {process_name} lock.")
        except Exception as e:
            logger.error(f"Failed to release lock: {e}")
