import sys
import os
sys.path.append("/Users/mac/Desktop/Ivybound")
from dotenv import load_dotenv

# Load from .env explicitly
load_dotenv("/Users/mac/Desktop/Ivybound/.env")

# Mailreef integration check
try:
    from mailreef_automation.mailreef_client import MailreefClient
    
    api_key = os.environ.get("MAILREEF_API_KEY")
    print(f"Testing API Key: {api_key[:5]}...{api_key[-4:]}")
    
    client = MailreefClient(api_key=api_key)
    inboxes = client.get_inboxes()
    
    if inboxes:
        print(f"SUCCESS: Connected to Mailreef. Found {len(inboxes)} inboxes.")
        # Check first 5 items to verify server
        servers = set([i.get('server', 'Unknown') for i in inboxes])
        print(f"Detected Servers: {servers}")
    else:
        print("FAILED: No inboxes returned.")
        
except Exception as e:
    print(f"ERROR: {e}")
