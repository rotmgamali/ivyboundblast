import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.join(os.getcwd(), 'mailreef_automation'))

from mailreef_client import MailreefClient

load_dotenv()
api_key = os.getenv("MAILREEF_API_KEY")

client = MailreefClient(api_key=api_key)
inboxes = client.get_inboxes()

print(f"Total inboxes: {len(inboxes)}")
if inboxes:
    print(f"Sample inbox: {inboxes[0]}")
    for i, inbox in enumerate(inboxes[:10]):
         print(f"{i}: ID={inbox.get('id')} EMAIL={inbox.get('email')}")
