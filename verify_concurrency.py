
import threading
import time
import sys
import os
from collections import Counter

# Add automation dir to path
sys.path.append(os.path.join(os.path.dirname(__file__), "mailreef_automation"))

from contact_manager import ContactManager
from logger_util import get_logger

logger = get_logger("CONCURRENCY_TEST")

def simulate_inbox(inbox_id, results_list):
    """Simulate an inbox trying to claim a lead"""
    cm = ContactManager(database_path="mailreef_automation/campaign.db")
    leads = cm.get_pending_for_inbox(inbox_id=inbox_id, count=1, sequence_stage=1)
    if leads:
        email = leads[0]['email']
        results_list.append((inbox_id, email))
        logger.info(f"Inbox {inbox_id} claimed: {email}")
    else:
        logger.info(f"Inbox {inbox_id} got NO lead")

def run_concurrency_test():
    print("WARNING: This test claims leads in the LIVE database.")
    print("We will need to resets these claims or treat this as a dry-run confirmation.")
    
    threads = []
    results = []
    
    # Simulate 10 inboxes firing AT ONCE
    for i in range(1, 11):
        t = threading.Thread(target=simulate_inbox, args=(i, results))
        threads.append(t)
        
    print("🚀 Starting 10 simultaneous threads...")
    for t in threads:
        t.start()
        
    for t in threads:
        t.join()
        
    print("\nanalysis:")
    print(f"Total leads claimed: {len(results)}")
    
    emails = [r[1] for r in results]
    duplicates = [item for item, count in Counter(emails).items() if count > 1]
    
    if duplicates:
        print(f"❌ FATAL: Duplicate leads claimed! {duplicates}")
        exit(1)
    else:
        print("✅ SUCCESS: Zero duplicates found. Atomic locking is working.")
        
    # Optional: Release claims for production run (or just let them settle)
    # Theoretically, if we stop here, these leads remain 'claimed' which effectively 'burns' them for this test run unless we reset.
    # Since we want a clean start, we should probably reset claimed_by_inbox to NULL for these test IDs if we want them to be sent by real automation.
    # Or just leave them as 'test claims' and they won't be sent.
    # User said "reset test processes".
    # I'll reset the locks for these leads so the real run can pick them up?
    # Actually, verify_concurrency should probably roll back or we just accept 10 leads are 'burned' for test?
    # Better to reset them.
    
    reset_claims(results)

def reset_claims(results):
    cm = ContactManager(database_path="mailreef_automation/campaign.db")
    import sqlite3
    conn = sqlite3.connect(cm.db_path)
    cursor = conn.cursor()
    print("\nReleasing locks for test verification...")
    for inbox_id, email in results:
        cursor.execute("UPDATE contacts SET claimed_by_inbox = NULL, claimed_at = NULL WHERE email = ?", (email,))
    conn.commit()
    conn.close()
    print("Locks released.")

if __name__ == "__main__":
    run_concurrency_test()
