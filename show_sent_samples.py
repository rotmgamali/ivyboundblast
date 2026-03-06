
import sys
import os
import random
from datetime import datetime
from pathlib import Path

# Add project root and automation dir to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "mailreef_automation"))

from generators.email_generator import EmailGenerator
from sheets_integration import GoogleSheetsClient

def show_samples():
    print("Connecting to Sheets...")
    client = GoogleSheetsClient()
    client.setup_sheets()
    
    gen = EmailGenerator()
    
    records = client._fetch_all_records()
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Get leads sent today
    sent_today = [r for r in records if r.get('email_1_sent_at') and today_str in r.get('email_1_sent_at')]
    
    if not sent_today:
        print("No emails sent today found in the sheet.")
        return
        
    print(f"Found {len(sent_today)} emails sent today. Selecting 3 at random...")
    samples = random.sample(sent_today, min(3, len(sent_today)))
    
    for i, lead in enumerate(samples):
        print("\n" + "="*80)
        print(f"SAMPLE {i+1}: {lead.get('email')}")
        print(f"Recipient: {lead.get('first_name')} (Role: {lead.get('role')})")
        print(f"School: {lead.get('school_name')}")
        print(f"Sent At: {lead.get('email_1_sent_at')}")
        print("-"*80)
        
        # Determine sender based on inbox (if recorded) or default
        sender_email = lead.get('sender_email', 'andrew@ivybound.net')
        
        # Generate content
        # Note: This will call OpenAI and potentially scrape.
        # It's as close as we can get to the "live" sent email.
        try:
            content = gen.generate_for_lead(lead, sender_email=sender_email)
            print(f"SUBJECT: {content['subject']}")
            print(f"\n{content['greeting']}\n")
            print(content['body'])
            print(f"\n{content['sign_off']}")
        except Exception as e:
            print(f"Error generating sample: {e}")
            
    print("="*80)

if __name__ == "__main__":
    show_samples()
