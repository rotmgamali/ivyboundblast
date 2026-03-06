
import sys
import os
import requests
import json
# Add project root and automation dir to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "mailreef_automation"))

from mailreef_automation.mailreef_client import MailreefClient

def deep_dive():
    api_key = os.getenv("MAILREEF_API_KEY")
    if not api_key:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("MAILREEF_API_KEY")
        
    client = MailreefClient(api_key=api_key)
    
    print("Fetching domains (page 1)...")
    response = client.session.get(f"{client.base_url}/domains", params={"page": 1})
    if not response.ok:
        print(f"Domains Error: {response.status_code} - {response.text}")
        return
        
    domains = response.json().get('data', [])
    if not domains:
        print("No domains found.")
        return
        
    domain_id = domains[0].get('id')
    print(f"Domain: {domains[0].get('domain')} (ID: {domain_id})")
    
    print(f"Fetching mailboxes for domain {domain_id}...")
    response = client.session.get(f"{client.base_url}/mailboxes", params={"domain": domain_id, "page": 1})
    if not response.ok:
        print(f"Mailboxes Error: {response.status_code} - {response.text}")
        return
        
    mailboxes = response.json().get('data', [])
    if not mailboxes:
        print("No mailboxes found in this domain.")
        return
        
    inbox = mailboxes[0]
    inbox_id = inbox.get('id')
    email = inbox.get('email')
    print(f"Inbox: {email} (ID: {inbox_id})")
    
    # Try different types
    for t in ["sent", "received"]:
        print(f"\nChecking type: {t}...")
        url = f"{client.base_url}/mailboxes/{inbox_id}/messages"
        # Probable requirement: page parameter
        params = {"type": t, "page": 1, "display": 10}
        
        response = client.session.get(url, params=params)
        if response.ok:
            data = response.json()
            msgs = data.get('data', [])
            print(f"Found {len(msgs)} {t} messages.")
            for m in msgs[:3]:
                print(f"  - Subject: {m.get('subject')} | From: {m.get('from_email')} | Date: {m.get('date')}")
        else:
            print(f"Error {response.status_code}: {response.text}")

if __name__ == "__main__":
    deep_dive()
