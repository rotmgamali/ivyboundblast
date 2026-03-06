
import sys
import os
import requests
# Add project root and automation dir to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "mailreef_automation"))

from mailreef_automation.mailreef_client import MailreefClient

def check_one_inbox():
    api_key = os.getenv("MAILREEF_API_KEY")
    if not api_key:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("MAILREEF_API_KEY")
        
    client = MailreefClient(api_key=api_key)
    
    inboxes = client.get_inboxes()
    if not inboxes:
        print("No inboxes found.")
        return
        
    inbox = inboxes[0]
    inbox_id = inbox.get("id")
    email = inbox.get("email")
    print(f"Checking {email}...")
    
    # Try different message types: sent, received, all
    types = ["sent", "received"]
    for t in types:
        url = f"{client.base_url}/mailboxes/{inbox_id}/messages"
        params = {"type": t, "display": 5}
        try:
            response = client.session.get(url, params=params)
            if response.ok:
                data = response.json()
                msgs = data.get('data', data) if isinstance(data, dict) else data
                if isinstance(msgs, dict): msgs = msgs.get('messages', [])
                print(f"Type '{t}': Found {len(msgs)} messages.")
                if msgs:
                    for m in msgs:
                        print(f"  - Subject: {m.get('subject')} | From: {m.get('from_email')}")
            else:
                print(f"Type '{t}': Error {response.status_code}")
        except Exception as e:
            print(f"Type '{t}': Exception {e}")

if __name__ == "__main__":
    check_one_inbox()
