
import sys
import os
import sqlite3
import json

# Add project root path
sys.path.append(os.path.join(os.path.dirname(__file__), "mailreef_automation"))
sys.path.append(os.path.dirname(__file__))

from generators.email_generator import EmailGenerator
# Need to mock the scraper if I can't import easily or just use real one
from automation_scrapers.school_scraper import scrape_website_text

def inspect_content():
    db_path = "mailreef_automation/campaign.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get a random active lead that hasn't been sent yet
    # We want one with a valid domain
    cursor.execute("""
        SELECT * FROM contacts 
        WHERE status='active' AND domain IS NOT NULL ORDER BY RANDOM() LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print("No active leads found to inspect.")
        return

    lead = dict(row)
    print(f"🔎 INSPECTING LEAD: {lead['email']}")
    print(f"   School: {lead['school_name']}")
    print(f"   Role: {lead['role']}")
    print(f"   Domain: {lead['domain']}")
    print("-" * 50)
    
    # Run the generator
    generator = EmailGenerator()
    
    # 1. Scrape
    url = lead['domain']
    if not url.startswith("http"): url = "https://" + url
    
    print(f"🌍 Live Scraping {url}...")
    try:
        content = scrape_website_text(url)
        print(f"✅ Scrape Success ({len(content)} chars)")
        print(f"   Preview: {content[:200]}...")
    except Exception as e:
        print(f"❌ Scrape Failed: {e}")
        content = ""
        
    print("-" * 50)
    print("🧠 Generating Email with GPT-4o-mini...")
    
    result = generator.generate_email(
        campaign_type="school",
        sequence_number=1,
        lead_data=lead,
        enrichment_data={"website_content": content}
    )
    
    print("=" * 50)
    print(f"SUBJECT: {result['subject']}")
    print("-" * 50)
    print(result['body'])
    print("=" * 50)
    
    # Hallucination Check
    print("\n🕵️‍♀️ HALLUCINATION CHECK:")
    if result['body'].find(lead['city'] or "XXXX") != -1:
        print("✅ City context used correctly.")
    else:
        print("⚠️ City context missing or mismatch.")
        
    if "program" in result['body'].lower() or "mission" in result['body'].lower():
        print("✅ Program/Mission references found (likely from scrape).")
    else:
        print("ℹ️ No specific program referenced (generic template used?).")

if __name__ == "__main__":
    inspect_content()
