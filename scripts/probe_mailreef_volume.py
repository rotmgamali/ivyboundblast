import os
import sys
import requests
from mailreef_automation.mailreef_client import MailreefClient
import mailreef_automation.automation_config as automation_config

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "mailreef_automation"))

def analyze_mailreef_volume():
    api_key = os.getenv("MAILREEF_API_KEY")
    mailreef = MailreefClient(api_key=api_key)
    
    # Get all inboxes
    print("📡 Fetching all inboxes from Mailreef...")
    all_inboxes = mailreef.get_inboxes()
    all_inboxes.sort(key=lambda x: x['id'])
    
    campaigns = {
        "IVYBOUND": automation_config.CAMPAIGN_PROFILES["IVYBOUND"]["inbox_indices"],
        "STRATEGY_B": automation_config.CAMPAIGN_PROFILES["STRATEGY_B"]["inbox_indices"],
        "WEB4GURU_ACCOUNTANTS": automation_config.CAMPAIGN_PROFILES["WEB4GURU_ACCOUNTANTS"]["inbox_indices"]
    }
    
    print("\n🚀 Analyzing outbound volume per campaign (Estimated)...")
    
    total_web4guru = 0
    
    for name, indices in campaigns.items():
        start, end = indices
        campaign_inboxes = all_inboxes[start:end]
        
        campaign_count = 0
        print(f"\n📊 Campaign: {name} ({len(campaign_inboxes)} inboxes)")
        
        # We can't easily check 'all sent' for all inboxes without many API calls.
        # But maybe we can check analytics?
        # Let's try to get stats for the first few and extrapolate, or check if /mail/outbound works with display=1000
        
        # Try global outbound first
        try:
            # Note: Mailreef might not have a global /mail/outbound. 
            # If it doesn't, we'll have to loop.
            pass
        except:
            pass
            
    # Alternative: Mailreef has a /logs or similar?
    # Actually, the user wants "not warm up emails".
    # Mailreef stats usually *include* warmup. 
    # The Google Sheets status is the gold standard for "intentional sends".
    
    print("\n⚠️ NOTE: Mailreef API stats include warmup. Google Sheets reflects campaign intent.")

if __name__ == "__main__":
    analyze_mailreef_volume()
