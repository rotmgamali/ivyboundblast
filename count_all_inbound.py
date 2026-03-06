import os
from mailreef_automation.mailreef_client import MailreefClient
from dotenv import load_dotenv

load_dotenv()

def count_emails():
    client = MailreefClient(api_key=os.getenv("MAILREEF_API_KEY"))
    total = 0
    page = 1
    print("📡 Counting every single email in the Mailreef inbound queue...")
    
    while True:
        result = client.get_global_inbound(page=page, display=100)
        batch = result.get("data", [])
        batch_len = len(batch)
        total += batch_len
        
        print(f"  - Page {page}: {batch_len} emails (Total so far: {total})")
        
        if batch_len < 100 or page >= 100: # Safety cap
            break
        page += 1
        
    print("\n" + "="*40)
    print(f"📊 UNFILTERED TOTAL: {total}")
    print("="*40)

if __name__ == "__main__":
    count_emails()
