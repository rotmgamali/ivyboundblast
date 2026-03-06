import sys
import os
import pytz
from datetime import datetime
from unittest.mock import MagicMock
# Mock random to avoid issues with randint in the script execution context
import random
random.randint = MagicMock(return_value=30)

from mailreef_automation.scheduler import EmailScheduler
from mailreef_automation import automation_config

def verify_high_volume():
    print("--- Verifying High-Volume Slot Generation ---")
    profile_name = "WEB4GURU_ACCOUNTANTS"
    
    # Mock Mailreef
    mock_mailreef = MagicMock()
    # We need to return enough inboxes so that after indexing (0, 95) we get 95
    mock_inboxes = [{"id": f"inbox_{i}", "email": f"test_{i}@example.com"} for i in range(100)]
    mock_mailreef.get_inboxes.return_value = mock_inboxes
    
    # Mock Sheets
    sys.modules['sheets_integration'] = MagicMock()
    
    # Initialize Scheduler
    scheduler = EmailScheduler(mock_mailreef, automation_config, profile_name)
    
    print(f"Profile: {profile_name}")
    print(f"Emails per inbox (Business Limit): {automation_config.EMAILS_PER_INBOX_DAY_BUSINESS}")
    
    # Generate slots for business day
    # generate_send_slots(day_type, inbox_count)
    slots = scheduler.generate_send_slots("business", 95)
    
    total_slots = len(slots)
    # Expected: 10 windows * emails_per_inbox per window
    # Let's count emails_per_inbox in config
    total_per_inbox = sum(w["emails_per_inbox"] for w in automation_config.BUSINESS_DAY_WINDOWS)
    expected_slots = 95 * total_per_inbox
    
    print(f"\nTotal Slots Generated: {total_slots}")
    print(f"Expected Slots (95 * {total_per_inbox}): {expected_slots}")
    
    if total_slots == expected_slots:
        print("\n✅ SUCCESS: Schedule generated correctly!")
    else:
        print(f"\n❌ FAILURE: Expected {expected_slots}, got {total_slots}")
        
    # Spot check one inbox
    inbox_id_0 = mock_inboxes[0]["id"]
    inbox_0_slots = [s for s in slots if s["inbox_id"] == inbox_id_0]
    print(f"Slots for {inbox_id_0}: {len(inbox_0_slots)}")
    
    if len(inbox_0_slots) == total_per_inbox:
        print(f"✅ Slot count per inbox ({total_per_inbox}) is correct.")
    else:
        print(f"❌ Incorrect slot count for inbox: {len(inbox_0_slots)}")

if __name__ == "__main__":
    verify_high_volume()
