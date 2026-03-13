import time
import os
import csv
from dotenv import load_dotenv

from scraper.apify_maps import run_scraper
from researcher.serp_enricher import enrich_lead
from content.generator import generate_pitch
from lead_storage import LeadStorage
from sheets_integration import GoogleSheetsClient

# --- CONFIGURATION ---
TARGET_STATES = {
    "USA_TOP_50": [
        "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX", "Phoenix, AZ",
        "Philadelphia, PA", "San Antonio, TX", "San Diego, CA", "Dallas, TX", "San Jose, CA",
        "Austin, TX", "Jacksonville, FL", "Fort Worth, TX", "Columbus, OH", "Charlotte, NC",
        "San Francisco, CA", "Indianapolis, IN", "Seattle, WA", "Denver, CO", "Washington, DC",
        "Boston, MA", "El Paso, TX", "Nashville, TN", "Detroit, MI", "Oklahoma City, OK",
        "Portland, OR", "Las Vegas, NV", "Memphis, TN", "Louisville, KY", "Baltimore, MD",
        "Milwaukee, WI", "Albuquerque, NM", "Tucson, AZ", "Fresno, CA", "Mesa, AZ",
        "Sacramento, CA", "Atlanta, GA", "Kansas City, MO", "Colorado Springs, CO", "Miami, FL",
        "Raleigh, NC", "Omaha, NE", "Long Beach, CA", "Virginia Beach, VA", "Oakland, CA",
        "Minneapolis, MN", "Tulsa, OK", "Tampa, FL", "Arlington, TX", "New Orleans, LA"
    ]
}

CATEGORIES = [
    "Private School",
    "Public School",
    "Charter School",
    "Religious School",
    "Catholic School",
    "Islamic School",
    "Jewish School",
    "Montessori School",
    "Special Education School",
    "High School",
    "Elementary School",
    "Middle School",
    "Preparatory School",
    "Academy",
    "K-12 School",
    "School District" # Added for broader reach
]

# Production Settings
MAX_LEADS_PER_BATCH = 60 # Fetches up to 60 results per search term (covers most local maps grids)

# ---------------------

def load_processed_leads(csv_path):
    """
    Returns a set of processed titles to prevent duplicates.
    """
    processed = set()
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            next(reader, None) # Skip header
            for row in reader:
                if row:
                    processed.add(row[0].strip().lower()) # Title is index 0
    return processed

def harvest_state(state_code, cities, storage, processed_leads, sheets=None):
    print(f"\n🚜 STARTING HARVEST FOR STATE: {state_code}")
    
    for city in cities:
        for category in CATEGORIES:
            search_term = f"{category} in {city}, {state_code}"
            print(f"\n🔎 Searching: {search_term}...")
            
            try:
                # 1. Scrape
                raw_leads = run_scraper([search_term], max_items=MAX_LEADS_PER_BATCH)
                
                new_leads_count = 0
                for lead in raw_leads:
                    title = lead.get('title', '').strip()
                    
                    # Deduplication
                    if title.lower() in processed_leads:
                        print(f"   ⚠️ Skipping duplicate: {title}")
                        continue
                    
                    print(f"   Processing: {title}")
                    
                    # 2. Enrich
                    lead = enrich_lead(lead, "school")
                    
                    # 3. Generate (Improved Name Extraction)
                    school_name, email, sms = generate_pitch(lead)
                    lead['school_name'] = school_name
                    lead['generated_pitch'] = email
                    lead['sms_script'] = sms
                    
                    # 4. Save Locally
                    storage.log_lead(lead)
                    processed_leads.add(title.lower())
                    
                    # 5. Sync to Google Sheets
                    if sheets:
                        sheet_lead = {
                            "email": lead.get("email") or lead.get("company_email", ""),
                            "school_name": school_name, # Use AI extracted name
                            "school_type": lead.get("category", ""),
                            "city": lead.get("city") or city,
                            "state": lead.get("state") or state_code,
                            "phone": lead.get("phone") or lead.get("phoneNumber", ""),
                            "status": "pending",
                            "email_verified": "verified",
                            "custom_data": json.dumps({
                                "original_title": title,
                                "generated_pitch": email,
                                "sms_script": sms,
                                "website": lead.get("website", ""),
                                "address": lead.get("address", ""),
                                "recent_initiatives": lead.get("recent_initiatives", "")
                            })
                        }
                        
                        sheets.add_leads_batch([sheet_lead])
                        print(f"   📊 Synced to Google Sheets: {school_name} (from {title})")
                    
                    new_leads_count += 1
                    
                print(f"   ✅ Batch Complete. {new_leads_count} new leads added.")
                
            except Exception as e:
                print(f"   ❌ Batch Failed: {e}")
                
            # Respect rate limits
            time.sleep(2) 

    print(f"🏁 STATE COMPLETE: {state_code}.")

def main():
    load_dotenv()
    storage = LeadStorage()
    
    # Initialize Sheets Integration
    try:
        sheets = GoogleSheetsClient()
        sheets.setup_sheets()
        print("✅ Google Sheets connection established.")
    except Exception as e:
        print(f"⚠️ Google Sheets setup failed: {e}")
        sheets = None
    
    processed_leads = load_processed_leads(storage.csv_file)
    print(f"📚 Loaded {len(processed_leads)} existing leads for deduplication.")
    
    # Nation-wide Harvest
    if "USA_TOP_50" in TARGET_STATES:
        # We need to parse "City, ST" format
        formatted_cities = []
        for city_st in TARGET_STATES["USA_TOP_50"]:
            parts = city_st.split(',')
            if len(parts) == 2:
                formatted_cities.append( (parts[0].strip(), parts[1].strip()) )
        
        # We modify harvest_state to handle this or just iterate here
        print(f"🗺️  Scope: {len(formatted_cities)} Cities across USA.")
        
        for city, state in formatted_cities:
            harvest_state(state, [city], storage, processed_leads, sheets=sheets)

if __name__ == "__main__":
    main()
