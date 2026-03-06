
import sys
import os
import requests
# Add project root and automation dir to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "mailreef_automation"))

from mailreef_automation.mailreef_client import MailreefClient

def check_all_received():
    api_key = os.getenv("MAILREEF_API_KEY")
    if not api_key:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("MAILREEF_API_KEY")
        
    client = MailreefClient(api_key=api_key)
    
    print("Fetching inboxes...")
    inboxes = client.get_inboxes()
    print(f"Found {len(inboxes)} inboxes.")
    
    total_received = 0
    received_msgs = []
    
    for i, inbox in enumerate(inboxes):
        inbox_id = inbox.get("id")
        email = inbox.get("email")
        
        # print(f"Checking {email} ({i+1}/{len(inboxes)})...", end="\r")
        
        # Check for received messages
        url = f"{client.base_url}/mailboxes/{inbox_id}/messages"
        params = {"type": "received", "display": 50}
        
        try:
            response = client.session.get(url, params=params)
            if response.ok:
                data = response.json()
                # Handle batch structure
                msgs = data.get('data', data) if isinstance(data, dict) else data
                if isinstance(msgs, dict): msgs = msgs.get('messages', [])
                
                if msgs:
                    for m in msgs:
                        m["inbox_email"] = email
                        received_msgs.append(m)
                    total_received += len(msgs)
        except Exception as e:
            # print(f"\nError checking {email}: {e}")
            pass
            
    print(f"\nTotal Received Emails Found: {total_received}")
    
    if received_msgs:
        print("\n--- Samples ---")
        # Sort by date descending
        # received_msgs.sort(key=lambda x: x.get('date', ''), reverse=True)
        for msg in received_msgs[:10]:
            print(f"From: {msg.get('from_email')}")
            print(f"To: {msg.get('inbox_email')}")
            print(f"Subject: {msg.get('subject')}")
            print(f"Date: {msg.get('date')}")
            print("-" * 20)

if __name__ == "__main__":
    check_all_received()
