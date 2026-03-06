import os
import sys
import json

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "mailreef_automation"))

from mailreef_automation.mailreef_client import MailreefClient
import automation_config

def debug_inbound():
    mailreef = MailreefClient(api_key=automation_config.MAILREEF_API_KEY)
    print("📡 Fetching global inbound (Page 1)...")
    data = mailreef.get_global_inbound(page=1)
    
    print(f"DEBUG: Response keys: {data.keys() if isinstance(data, dict) else 'Not a dict'}")
    
    batch = data.get("data", []) if isinstance(data, dict) else data
    print(f"DEBUG: Batch size: {len(batch)}")
    
    if batch:
        print("\nDEBUG: First email sample:")
        sample = batch[0]
        # Recursively print keys and types
        for k, v in sample.items():
            print(f"  - {k} ({type(v).__name__}): {str(v)[:100]}")
    else:
        print("DEBUG: No emails found in batch.")

if __name__ == "__main__":
    debug_inbound()
