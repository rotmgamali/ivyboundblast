import os
import sys
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.getcwd())

from Jobs.researcher.serp_enricher import enrich_lead
from Jobs.content.generator import generate_pitch
from sheets_integration import GoogleSheetsClient

def scrape_url(url):
    """Simple scraper to simulate the crawler-google-places add-on."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Remove scripts and styles
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text()
        # Break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        return text[:10000] # Limit to 10k chars
    except Exception as e:
        print(f"⚠️ Failed to scrape {url}: {e}")
        return ""

def live_test():
    load_dotenv()
    
    # Selection of diverse real schools for testing
    test_urls = [
        "https://www.thegroveschool.org/", # Charter school in CA
        "https://www.stignatius-savannah.org/", # Catholic school in GA
        "https://www.harlemvillageacademies.org/" # Academy in NY
    ]
    
    print("\n🚀 STARTING LIVE PIPELINE TEST")
    
    sheets = None
    try:
        sheets = GoogleSheetsClient()
        sheets.setup_sheets()
        print("✅ Sheets Connected.")
    except Exception as e:
        print(f"⚠️ Sheets setup failed: {e}")

    for url in test_urls:
        print(f"\n--- Testing URL: {url} ---")
        
        # 1. Scrape "Live" Content
        print("📥 Fetching website content...")
        content = scrape_url(url)
        if not content:
            continue
            
        lead = {
            "title": "Finding accurate name...", # Will be overwritten by AI
            "website": url,
            "website_content": content,
            "address": "Auto-detected",
            "phone": "Auto-detected"
        }
        
        # 2. Enrich (Serper)
        print("🔬 Running SERP Enrichment...")
        lead = enrich_lead(lead, "school")
        
        # 3. Generate Personalized Pitch
        print("🧠 Generating Hyper-Personalized Pitch...")
        school_name, email, sms = generate_pitch(lead)
        lead['school_name'] = school_name
        lead['generated_pitch'] = email
        lead['sms_script'] = sms
        
        print(f"\n✅ SUCCESS: Identified as '{school_name}'")
        print("-" * 30)
        print(f"EMAIL PREVIEW:\n{email[:300]}...")
        print("-" * 30)
        
        # 4. Sync to Sheets
        if sheets:
            sheet_lead = {
                "email": "test@demo.com", # Mocking email for safety in these tests
                "school_name": school_name,
                "school_type": "Live Test",
                "city": "Test",
                "state": "TS",
                "phone": "N/A",
                "status": "pending",
                "email_verified": "verified",
                "custom_data": json.dumps({
                    "test_run": True,
                    "original_url": url,
                    "generated_pitch": email,
                    "sms_script": sms
                })
            }
            sheets.add_leads_batch([sheet_lead])
            print("📊 Synced to 'Ivy Bound - Scraped Leads'")

    print("\n🏁 LIVE PIPELINE TEST COMPLETE")

if __name__ == "__main__":
    live_test()
