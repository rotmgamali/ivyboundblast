import os
import sys
import json

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "mailreef_automation"))

from mailreef_automation.mailreef_client import MailreefClient
import automation_config

def diag():
    mailreef = MailreefClient(api_key=automation_config.MAILREEF_API_KEY)
    inboxes = mailreef.get_inboxes()
    if inboxes:
        print(f"DEBUG: Found {len(inboxes)} inboxes.")
        print(f"DEBUG: First inbox keys: {inboxes[0].keys()}")
        print(f"DEBUG: First inbox sample: {inboxes[0]}")
    else:
        print("DEBUG: No inboxes found.")

if __name__ == "__main__":
    diag()
