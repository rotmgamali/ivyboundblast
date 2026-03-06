import os
import json
import sys
import sys
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "mailreef_automation"))

from mailreef_client import MailreefClient

def check_one():
    mailreef = MailreefClient(api_key=os.getenv("MAILREEF_API_KEY"))
    data = mailreef.get_global_inbound(page=1, display=5)
    emails = data.get("data", [])
    
    if not emails:
        print("No emails found.")
        return
        
    for i, msg in enumerate(emails):
        print(f"\n--- EMAIL {i+1} ---")
        print(f"From: {msg.get('from_email')}")
        print(f"Subject: {msg.get('subject_line')}")
        print(f"Snippet: {msg.get('snippet_preview')}")
        print(f"Body Text Length: {len(msg.get('body_text', ''))}")
        print(f"Body HTML Length: {len(msg.get('body_html', ''))}")
        
        # Print a bit of each to see the difference
        print("\nBODY TEXT SAMPLE:")
        print(msg.get('body_text', '')[:500])
        
        print("\nBODY HTML STRIPPED SAMPLE:")
        import re
        html = msg.get('body_html', '')
        stripped = re.sub('<[^<]+?>', '', html)
        print(stripped[:500])
        
if __name__ == "__main__":
    check_one()
