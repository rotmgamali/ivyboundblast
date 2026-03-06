
import sys
import os
import requests
# Add project root and automation dir to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "mailreef_automation"))

from mailreef_automation.mailreef_client import MailreefClient

def debug_inboxes():
    api_key = os.getenv("MAILREEF_API_KEY")
    if not api_key:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("MAILREEF_API_KEY")
        
    client = MailreefClient(api_key=api_key)
    
    print("Fetching domains...")
    response = client.session.get(f"{client.base_url}/domains")
    if response.ok:
        data = response.json()
        domains = data.get('data', data) if isinstance(data, dict) else data
        print(f"Found {len(domains)} domains.")
        if domains:
            domain_id = domains[0].get('id')
            print(f"Sample Domain ID: {domain_id}")
            
            print(f"Fetching mailboxes for domain {domain_id}...")
            response = client.session.get(f"{client.base_url}/mailboxes", params={"domain": domain_id})
            if response.ok:
                data = response.json()
                print("Mailboxes Response Keys:", data.keys() if isinstance(data, dict) else "Not a dict")
                mailboxes = data.get('data', data) if isinstance(data, dict) else data
                print(f"Found {len(mailboxes)} mailboxes.")
                if mailboxes:
                    print("Sample Mailbox Keys:", mailboxes[0].keys())
                    print("Sample Mailbox:", mailboxes[0])
            else:
                print(f"Mailboxes Error: {response.status_code}")
    else:
        print(f"Domains Error: {response.status_code}")

if __name__ == "__main__":
    debug_inboxes()
