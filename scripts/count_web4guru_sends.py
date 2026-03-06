import os
import sys

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "mailreef_automation"))

from sheets_integration import GoogleSheetsClient
from logger_util import get_logger

logger = get_logger("SEND_ANALYSIS")

def analyze_web4guru_sends():
    # Campaign sheets to check
    campaigns = {
        "STRATEGY_B": "Web4Guru - Campaign Leads",
        "WEB4GURU_ACCOUNTANTS": "Web4Guru Accountants - Campaign Leads"
    }
    
    total_emails_sent = 0
    
    print("🚀 Analyzing Web4Guru sending volume (excluding warmup)...")
    
    for profile, sheet_name in campaigns.items():
        print(f"\n📊 Checking {profile} ({sheet_name})...")
        try:
            sheets = GoogleSheetsClient(input_sheet_name=sheet_name)
            sheets.setup_sheets() # <--- NEED THIS TO OPEN THE SHEETS
            # Fetch all records via the internal helper to leverage existing normalization/auth
            records = sheets._fetch_all_records()
            
            e1_count = 0
            e2_count = 0
            replied_count = 0
            
            for r in records:
                status = str(r.get('status', '')).lower()
                
                # Logic: 
                # If email_2_sent, then both email 1 and email 2 were sent (2 emails)
                # If email_1_sent, then only email 1 was sent (1 email)
                # If replied, usually both were sent (unless they replied to email 1). 
                # Let's check for 'email_2_sent_at' to be more precise if possible
                
                e1_sent_at = r.get('email_1_sent_at')
                e2_sent_at = r.get('email_2_sent_at')
                
                if e1_sent_at and e1_sent_at != "":
                    e1_count += 1
                if e2_sent_at and e2_sent_at != "":
                    e2_count += 1
                
                # Fallback if dates are missing but status is set
                if not e1_sent_at and status == 'email_1_sent':
                    e1_count += 1
                if not e2_sent_at and status == 'email_2_sent':
                    e1_count += 1 # Assume 1 was sent
                    e2_count += 1

            campaign_total = e1_count + e2_count
            total_emails_sent += campaign_total
            
            print(f"  - Leads with Email 1: {e1_count}")
            print(f"  - Leads with Email 2: {e2_count}")
            print(f"  - Total for this campaign: {campaign_total}")
            
        except Exception as e:
            print(f"  ❌ Error processing {profile}: {e}")

    print("\n" + "="*40)
    print(f"🏆 TOTAL WEB4GURU EMAILS SENT: {total_emails_sent}")
    print("="*40)

if __name__ == "__main__":
    analyze_web4guru_sends()
