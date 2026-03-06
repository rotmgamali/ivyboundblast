
import sys
import os
import json
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "mailreef_automation"))

from mailreef_client import MailreefClient
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("MAILREEF_API_KEY")
client = MailreefClient(api_key=API_KEY)

def inspect_body():
    print("🔍 Fetching latest inbound email to inspect body...")
    res = client.get_global_inbound(page=1, display=1)
    data = res.get("data", [])
    
    if data:
        msg = data[0]
        print(f"\nSubject: {msg.get('subject_line')}")
        print(f"Message ID: {msg.get('message_id')}")
        
        body_text = msg.get('body_text')
        snippet = msg.get('snippet_preview')
        history = msg.get('history')
        
        print(f"\n--- Body Text (Length: {len(body_text) if body_text else 0}) ---")
        print(body_text[:500] if body_text else "None")
        
        print(f"\n--- Snippet (Length: {len(snippet) if snippet else 0}) ---")
        print(snippet)
        
        print(f"\n--- History Field (Type: {type(history)}) ---")
        print(history)
        
    else:
        print("No emails found.")

if __name__ == "__main__":
    inspect_body()
