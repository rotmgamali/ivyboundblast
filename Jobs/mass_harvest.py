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

import json
import re

# ---- Decision-Maker Targeting ----
# Title keywords ranked by seniority (highest first)
DECISION_MAKER_TITLES = [
    # Tier 1: Ultimate authority
    ["superintendent", "executive director", "ceo", "president", "founder", "owner"],
    # Tier 2: Principal leadership
    ["principal", "head of school", "headmaster", "headmistress"],
    # Tier 3: Directors
    ["director of admissions", "director of education", "director of curriculum", "director"],
    # Tier 4: Academic leaders
    ["academic dean", "dean of students", "dean"],
    # Tier 5: Counselors / Advisors
    ["college counselor", "guidance counselor", "college advisor", "counselor", "advisor"],
    # Tier 6: Admissions / Enrollment (relevant to our pitch)
    ["admissions", "enrollment"],
]

# Email prefixes that are NOT decision makers (skip entirely)
GENERIC_EMAIL_PREFIXES = {
    "info", "admin", "office", "contact", "hello", "help", "support",
    "reception", "secretary", "webmaster", "noreply", "no-reply",
    "mail", "general", "inquiries", "inquiry", "registrar", "accounts"
}

def score_contact(email: str, title: str) -> int:
    """Return a priority score for a contact. Higher = more senior. -1 = disqualify."""
    if not email or "@" not in email:
        return -1
    # Strip URL-style values
    if email.startswith("http"):
        return -1
    # Check prefix against generic blocklist
    prefix = email.split("@")[0].lower().strip()
    if prefix in GENERIC_EMAIL_PREFIXES:
        return -1
    # Score by title
    title_lower = (title or "").lower()
    for tier, keywords in enumerate(DECISION_MAKER_TITLES):
        if any(kw in title_lower for kw in keywords):
            return len(DECISION_MAKER_TITLES) - tier  # Higher tier = higher score
    # Unknown title — assign lowest passing score (still better than generic)
    return 0

def select_top_decision_makers(contacts: list, max_contacts: int = 3) -> list:
    """
    Given a list of dicts with 'email' and 'title', return the top N decision makers.
    contacts: [{"email": "...", "title": "..."}, ...]
    """
    scored = []
    seen_emails = set()
    for c in contacts:
        email = (c.get("email") or "").strip().lower()
        title = c.get("title", "")
        if not email or email in seen_emails:
            continue
        score = score_contact(email, title)
        if score >= 0:  # -1 means disqualified
            scored.append((score, email, title, c))
            seen_emails.add(email)
    # Sort descending by score
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[3] for item in scored[:max_contacts]]
# ----------------------------------

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
        all_city_terms = [f"{category} in {city}, {state_code}" for category in CATEGORIES]
        print(f"\n🔎 Batch searching {len(all_city_terms)} categories for {city}, {state_code}...")
        
        try:
            # 1. Scrape (Batch)
            raw_leads = run_scraper(all_city_terms, max_items=MAX_LEADS_PER_BATCH)
            
            new_leads_count = 0
            for lead in raw_leads:
                title = lead.get('title', '').strip()
                
                # Deduplication
                if title.lower() in processed_leads:
                    # Skip noise for skipped duplicates
                    continue
                
                print(f"   Processing: {title}")
                
                # 2. Enrich
                lead = enrich_lead(lead, "school")
                
                # 3. Decision-Maker Targeting: Extract, score, and limit to top 3
                # Apify returns emails in lead['emails'] (list of dicts) or lead['email'] (single str)
                raw_contacts = []
                if lead.get("emails") and isinstance(lead["emails"], list):
                    for e in lead["emails"]:
                        raw_contacts.append({
                            "email": e.get("value", "") if isinstance(e, dict) else str(e),
                            "title": e.get("description", "") if isinstance(e, dict) else ""
                        })
                elif lead.get("email"):
                    raw_contacts.append({"email": lead["email"], "title": lead.get("role", "")})

                top_contacts = select_top_decision_makers(raw_contacts, max_contacts=3)

                if not top_contacts:
                    print(f"   ⚠️  No valid decision-maker emails found for {title}. Skipping.")
                    processed_leads.add(title.lower())
                    continue

                primary_contact = top_contacts[0]
                primary_email = primary_contact["email"]
                additional_emails = {c["email"]: c.get("title", "") for c in top_contacts[1:]}

                school_name, email_pitch, sms = generate_pitch(lead)
                lead['school_name'] = school_name
                lead['generated_pitch'] = email_pitch
                lead['sms_script'] = sms

                # 4. Save Locally
                storage.log_lead(lead)
                processed_leads.add(title.lower())

                # 5. Sync to Google Sheets (primary + up to 2 extras in custom_data)
                if sheets:
                    extra_contacts_json = json.dumps(additional_emails) if additional_emails else "{}"
                    sheet_lead = {
                        "email": primary_email,
                        "school_name": school_name,
                        "school_type": lead.get("category", ""),
                        "city": lead.get("city") or city,
                        "state": lead.get("state") or state_code,
                        "phone": lead.get("phone") or lead.get("phoneNumber", ""),
                        "status": "pending",
                        "email_verified": "verified",
                        "custom_data": json.dumps({
                            "original_title": title,
                            "generated_pitch": email_pitch,
                            "sms_script": sms,
                            "website": lead.get("website", ""),
                            "address": lead.get("address", ""),
                            "recent_initiatives": lead.get("recent_initiatives", ""),
                            **additional_emails  # Spread extra decision-maker emails into custom_data
                        })
                    }
                    sheets.add_leads_batch([sheet_lead])
                    contact_summary = f"{primary_email}" + (f" + {len(additional_emails)} more" if additional_emails else "")
                    print(f"   📊 Synced to Sheets: {school_name} → {contact_summary}")
                
                new_leads_count += 1
                
            print(f"   ✅ City Complete. {new_leads_count} new leads added.")
            
        except Exception as e:
            print(f"   ❌ City Batch Failed: {e}")
            
        # Respect rate limits between cities
        time.sleep(5) 

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
