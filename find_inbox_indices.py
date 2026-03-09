import sys
import os
sys.path.append("/Users/mac/Desktop/Ivybound")
from dotenv import load_dotenv

load_dotenv("/Users/mac/Desktop/Ivybound/.env")

try:
    from mailreef_automation.mailreef_client import MailreefClient
    
    api_key = os.environ.get("MAILREEF_API_KEY")
    client = MailreefClient(api_key=api_key)
    inboxes = client.get_inboxes()
    
    if inboxes:
        print(f"Total inboxes: {len(inboxes)}")
        errorskin_indices = [i for i, x in enumerate(inboxes) if x.get('server') == 'errorskin']
        birdsgeese_indices = [i for i, x in enumerate(inboxes) if x.get('server') == 'birdsgeese']
        
        print(f"Errorskin indices: {min(errorskin_indices)} to {max(errorskin_indices)} (Total: {len(errorskin_indices)})")
        print(f"Birdsgeese indices: {min(birdsgeese_indices)} to {max(birdsgeese_indices)} (Total: {len(birdsgeese_indices)})")
except Exception as e:
    print(f"ERROR: {e}")
