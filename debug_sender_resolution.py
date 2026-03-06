import os
import sys
import json
from dotenv import load_dotenv

# Path setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mailreef_automation'))

from mailreef_automation.mailreef_client import MailreefClient

load_dotenv()

def debug_sender_resolution():
    print("--- 🕵️‍♂️ Debugging Sender Resolution ---")
    
    api_key = os.getenv("MAILREEF_API_KEY")
    if not api_key:
        print("❌ API Key not found in env.")
        return

    client = MailreefClient(api_key=api_key)
    
    try:
        print("Fetching inboxes from Mailreef API...")
        inboxes = client.get_inboxes()
        print(f"✅ Fetched {len(inboxes)} inboxes.")
        
        if len(inboxes) == 0:
            print("⚠️ No inboxes returned!")
            return

        # Simulate the lookup logic used in scheduler.py
        test_inbox = inboxes[0]
        test_id = test_inbox['id']
        expected_email = test_inbox['email']
        
        print(f"\nTest Lookup for ID: {test_id} (Expected: {expected_email})")
        
        # Exact logic from scheduler.py
        resolved_email = "unknown"
        for ibx in inboxes:
            # Note: scheduler uses str conversion
            if str(ibx['id']) == str(test_id):
                resolved_email = ibx['email'] or ibx.get('address', 'unknown')
                break
        
        print(f"Resolved Email: {resolved_email}")
        
        if resolved_email == expected_email:
            print("✅ PASS: Lookup logic works correctly.")
        else:
            print(f"❌ FAIL: Lookup logic mismatch. Got {resolved_email}, expected {expected_email}")
            
    except Exception as e:
        print(f"❌ API Error: {e}")

if __name__ == "__main__":
    debug_sender_resolution()
