import sys
import os
import argparse
import sqlite3
from tabulate import tabulate # Requires 'tabulate', if not installed we can fallback

# Add automation dir to path
sys.path.append(os.path.join(os.path.dirname(__file__), "mailreef_automation"))

from contact_manager import ContactManager
from headers import *

DB_PATH = "mailreef_automation/campaign.db"

def list_stuck_locks(args):
    """List all leads locked for more than 1 hour"""
    cm = ContactManager(database_path=DB_PATH)
    stale_leads = cm.scan_stale_locks()
    
    if not stale_leads:
        print("✅ No stale locks found.")
        return

    print(f"⚠️ Found {len(stale_leads)} stale locks:")
    table = []
    for lead in stale_leads:
        table.append([
            lead['id'], 
            lead['email'], 
            lead['claimed_by_inbox'], 
            lead['claimed_at']
        ])
    
    # Simple table print if tabulate missing
    print(f"{'ID':<5} | {'Email':<30} | {'Inbox':<25} | {'Claimed At'}")
    print("-" * 80)
    for row in table:
        print(f"{row[0]:<5} | {row[1]:<30} | {row[2]:<25} | {row[3]}")

def release_lock(args):
    """Release lock for a specific email"""
    email = args.email
    if not email:
        print("Please provide an email with --email")
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT claimed_by_inbox FROM contacts WHERE email = ?", (email,))
    row = cursor.fetchone()
    
    if not row or not row[0]:
        print(f"No lock found for {email}")
        conn.close()
        return
        
    print(f"Releasing lock for {email} (held by {row[0]})...")
    cursor.execute("""
        UPDATE contacts 
        SET claimed_by_inbox = NULL, claimed_at = NULL 
        WHERE email = ?
    """, (email,))
    conn.commit()
    conn.close()
    print("✅ Lock released. Lead returns to pool.")

def mark_failed(args):
    """Mark a stuck lead as failed (do not retry)"""
    email = args.email
    if not email:
        print("Please provide an email with --email")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"Marking {email} as FAILED (stuck lock)...")
    # We can fake a send_log entry with status 'failed' to prevent retry
    # Or just set status='failed' if column exists? status='active' is main trigger.
    # Set status='stuck_error'
    
    cursor.execute("UPDATE contacts SET status = 'stuck_error' WHERE email = ?", (email,))
    # Release lock so it doesn't show up in audit, but status prevents resend
    cursor.execute("UPDATE contacts SET claimed_by_inbox = NULL, claimed_at = NULL WHERE email = ?", (email,))
    
    conn.commit()
    conn.close()
    print("✅ Lead marked as 'stuck_error'. Will not be retried.")

def main():
    parser = argparse.ArgumentParser(description="Manage Stale Locks")
    subparsers = parser.add_subparsers()
    
    # List command
    parser_list = subparsers.add_parser('list', help='List stale locks')
    parser_list.set_defaults(func=list_stuck_locks)
    
    # Release command
    parser_release = subparsers.add_parser('release', help='Release a lock (retry)')
    parser_release.add_argument('--email', required=True, help='Email to release')
    parser_release.set_defaults(func=release_lock)
    
    # Fail command
    parser_fail = subparsers.add_parser('fail', help='Mark as failed (no retry)')
    parser_fail.add_argument('--email', required=True, help='Email to fail')
    parser_fail.set_defaults(func=mark_failed)
    
    if len(sys.argv) < 2:
        parser.print_help()
        return
        
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
