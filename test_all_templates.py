"""
Test All Templates - Generate and Send via Mailreef

Generates emails for all 9 archetypes × 2 sequences = 18 emails
and sends them to a test address via Mailreef API.
"""

import os
import sys
import time
import warnings
warnings.filterwarnings('ignore')

# Add project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generators.email_generator import EmailGenerator
from mailreef_automation.mailreef_client import MailreefClient
from dotenv import load_dotenv

load_dotenv()

# Test recipient
TEST_EMAIL = "andrew@web4guru.com"

# Mailreef Config
MAILREEF_API_KEY = os.getenv("MAILREEF_API_KEY")

# All archetypes with sample leads
ARCHETYPES = {
    "principal": {
        "first_name": "Michael",
        "role": "Assistant Principal",
        "school_name": "Pine Crest School",
        "city": "Fort Lauderdale",
        "state": "FL",
        "subtypes": "Private, Independent, Co-educational",
        "domain": "pinecrest.edu"
    },
    "head_of_school": {
        "first_name": "Patrick",
        "role": "Head of School",
        "school_name": "Palmer Trinity School",
        "city": "Miami",
        "state": "FL",
        "subtypes": "Episcopal, Independent",
        "domain": "palmertrinity.org"
    },
    "academic_dean": {
        "first_name": "Maria",
        "role": "Dean of Academics",
        "school_name": "Gulliver Preparatory School",
        "city": "Coral Gables",
        "state": "FL",
        "subtypes": "Private, Co-educational",
        "domain": "gulliverprep.org"
    },
    "college_counseling": {
        "first_name": "Robert",
        "role": "Director of College Counseling",
        "school_name": "Westminster Christian School",
        "city": "Palmetto Bay",
        "state": "FL",
        "subtypes": "Christian, Private",
        "domain": "wcsmiami.org"
    },
    "business_manager": {
        "first_name": "Linda",
        "role": "Business Manager",
        "school_name": "Ransom Everglades School",
        "city": "Coconut Grove",
        "state": "FL",
        "subtypes": "Private, Independent",
        "domain": "ransomeverglades.org"
    },
    "faith_leader": {
        "first_name": "Father",
        "role": "Campus Minister",
        "school_name": "Belen Jesuit Preparatory School",
        "city": "Miami",
        "state": "FL",
        "subtypes": "Catholic, Jesuit, All-boys",
        "domain": "belenjesuit.org"
    },
    "athletics": {
        "first_name": "Coach",
        "role": "Athletic Director",
        "school_name": "Columbus High School",
        "city": "Miami",
        "state": "FL",
        "subtypes": "Catholic, Marist, All-boys",
        "domain": "columbushs.com"
    },
    "admissions": {
        "first_name": "Jennifer",
        "role": "Director of Admissions",
        "school_name": "Saint Andrew's School",
        "city": "Boca Raton",
        "state": "FL",
        "subtypes": "Episcopal, Independent, Boarding",
        "domain": "saintandrews.net"
    },
    "general": {
        "first_name": "Sarah",
        "role": "Administrator",
        "school_name": "American Heritage Schools",
        "city": "Plantation",
        "state": "FL",
        "subtypes": "Private, Non-sectarian",
        "domain": "ahschool.com"
    }
}


def main():
    generator = EmailGenerator()
    
    print("\n" + "="*60)
    print("GENERATING ALL 18 TEMPLATE EMAILS")
    print(f"Sending to: {TEST_EMAIL}")
    print("="*60)
    
    # Setup Mailreef client
    mailreef = None
    inbox_id = None
    
    if MAILREEF_API_KEY:
        try:
            mailreef = MailreefClient(MAILREEF_API_KEY)
            print("\n🔌 Connecting to Mailreef...")
            inboxes = mailreef.get_inboxes()
            if inboxes:
                # Use first available inbox
                inbox_id = inboxes[0].get('id')
                inbox_email = inboxes[0].get('email', inboxes[0].get('address', 'unknown'))
                print(f"✓ Found {len(inboxes)} inboxes. Using: {inbox_email}")
            else:
                print("⚠️ No inboxes found in Mailreef")
        except Exception as e:
            print(f"⚠️ Mailreef connection failed: {e}")
    else:
        print("⚠️ No MAILREEF_API_KEY configured")
    
    emails_generated = []
    
    for archetype, lead in ARCHETYPES.items():
        print(f"\n[{archetype.upper()}] Generating emails...")
        
        for seq in [1, 2]:
            print(f"  Email #{seq}...", end=" ")
            
            try:
                result = generator.generate_email(
                    campaign_type="school",
                    sequence_number=seq,
                    lead_data=lead,
                    enrichment_data={}  # Will scrape live
                )
                
                if result['subject'] and result['body']:
                    print(f"✓ Generated ({len(result['body'])} chars)")
                    emails_generated.append({
                        "archetype": archetype,
                        "sequence": seq,
                        "lead": lead,
                        "result": result
                    })
                else:
                    print(f"✗ Empty result")
                    
            except Exception as e:
                print(f"✗ Error: {e}")
            
            time.sleep(0.5)  # Rate limit between generations
    
    print(f"\n{'='*60}")
    print(f"GENERATED: {len(emails_generated)}/18 emails")
    print(f"{'='*60}")
    
    # Print all to console
    for email in emails_generated:
        print(f"\n{'='*60}")
        print(f"ARCHETYPE: {email['archetype'].upper()} | EMAIL #{email['sequence']}")
        print(f"{'='*60}")
        print(f"SUBJECT: {email['result']['subject']}")
        print(f"-"*60)
        print(email['result']['body'])
    
    # Send via Mailreef if available
    if mailreef and inbox_id:
        print(f"\n{'='*60}")
        print("SENDING EMAILS VIA MAILREEF...")
        print(f"{'='*60}")
        
        sent_count = 0
        for email in emails_generated:
            try:
                subject = f"[TEST {email['archetype'].upper()} #{email['sequence']}] {email['result']['subject']}"
                body_html = email['result']['body'].replace('\n', '<br>')
                
                mailreef.send_email(
                    inbox_id=inbox_id,
                    to_email=TEST_EMAIL,
                    subject=subject,
                    body=f"<html><body style='font-family: Arial;'>{body_html}</body></html>"
                )
                print(f"  ✓ Sent: {email['archetype']} #{email['sequence']}")
                sent_count += 1
                time.sleep(5)  # Rate limit
                
            except Exception as e:
                print(f"  ✗ Failed {email['archetype']} #{email['sequence']}: {e}")
        
        print(f"\n✅ Sent {sent_count}/{len(emails_generated)} emails to {TEST_EMAIL}")
    else:
        print("\n⚠️ Mailreef not available. Emails printed above but not sent.")


if __name__ == "__main__":
    main()
