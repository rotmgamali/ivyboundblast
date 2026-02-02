import logging
import argparse
import json
from datetime import datetime
from typing import Dict, Any, List, Set

import sys
import os

# Add automation dir to path
sys.path.append(os.path.join(os.path.dirname(__file__), "mailreef_automation"))

from contact_manager import ContactManager
from sheets_integration import GoogleSheetsClient

# Configure logging
logging.getLogger('googleapiclient').setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

SOURCE_SHEET_NAME = "Ivy Bound - High & Middle Schools (Validated)"
TARGET_SHEET_NAME = "Ivy Bound - Campaign Leads"

def parse_name(full_name: str) -> tuple:
    """Split full name into first and last."""
    if not full_name:
        return "", ""
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])

def map_lead(record: Dict[str, Any]) -> Dict[str, str]:
    """Map source record to target schema with enhanced personalization data."""
    
    # Contact Name: Try owner_title, else blank
    contact_name = str(record.get('owner_title', '')).strip()
    first, last = parse_name(contact_name)
    
    # Phone
    phone = str(record.get('phone', '') or record.get('company_insights.phone', '')).strip()
    
    # Website
    website = str(record.get('site', '') or record.get('website', '')).strip()
    
    # Location
    city = str(record.get('city', '') or record.get('company_insights.city', '')).strip()
    state = str(record.get('state', '') or record.get('company_insights.state', '')).strip()
    full_address = str(record.get('full_address', '')).strip()
    
    # Enrichment Fields for Personalization
    rating = str(record.get('rating', '')).strip()
    reviews_count = str(record.get('reviews', '') or record.get('reviews_count', '')).strip()
    description = str(record.get('description', '') or record.get('about', '')).strip()[:500]  # Truncate
    subtypes = str(record.get('subtypes', '')).strip()
    founded_year = str(record.get('company_insights.founded_year', '')).strip()
    
    # Determine Role from subtypes (e.g., "Catholic school" -> role context)
    role = subtypes.split(',')[0].strip() if subtypes else "School Staff"
    
    return {
        "email": str(record.get('email', '')).strip(),
        "first_name": first,
        "last_name": last,
        "role": role,
        "school_name": str(record.get('name', '')).strip(),
        "domain": website,
        "state": state,
        "city": city,
        "full_address": full_address,
        "phone": phone,
        "rating": rating,
        "reviews_count": reviews_count,
        "description": description,
        "subtypes": subtypes,
        "founded_year": founded_year,
        "status": "pending",
        "email_1_sent_at": "",
        "email_2_sent_at": "",
        "sender_email": "",
        "notes": f"Imported {datetime.now().strftime('%Y-%m-%d')}. Val: {record.get('email.emails_validator.status')}"
    }

def run_import(dry_run: bool = True):
    logger.info("Initializing Google Sheets client...")
    client = GoogleSheetsClient()
    
    # --- 1. Load Source Data ---
    try:
        source_sheet = client.client.open(SOURCE_SHEET_NAME).sheet1
        logger.info(f"Reading source: {SOURCE_SHEET_NAME}...")
        source_records = source_sheet.get_all_records()
        logger.info(f"Source records loaded: {len(source_records)}")
    except Exception as e:
        logger.error(f"Failed to load source sheet: {e}")
        return

    # --- 2. Load Target Data (for duplicates) ---
    try:
        # Assuming we can access the target sheet configured in sheets_integration
        # If the names match what's in the config, we can use the client's helper keys if setup, 
        # but better to open by name to be safe.
        target_sheet = client.client.open(TARGET_SHEET_NAME).sheet1
        logger.info(f"Reading target: {TARGET_SHEET_NAME}...")
        target_records = target_sheet.get_all_records()
        existing_emails: Set[str] = {str(r.get('email', '')).lower().strip() for r in target_records if r.get('email')}
        logger.info(f"Existing leads in target: {len(existing_emails)}")
    except Exception as e:
        logger.error(f"Failed to load target sheet: {e}")
        return

    # --- 3. Filter and Prepare ---
    to_import = []
    all_valid_leads = []
    skipped_status = 0
    skipped_dupe = 0
    skipped_no_email = 0

    logger.info("Processing records...")
    
    for record in source_records:
        # Check Business Status
        biz_status = str(record.get('business_status', '')).upper()
        if biz_status != 'OPERATIONAL':
            skipped_status += 1
            continue
            
        # Check Email Validation
        email_status = str(record.get('email.emails_validator.status', '')).upper()
        if email_status != 'RECEIVING':
            skipped_status += 1
            continue
            
        # Check Email Existence
        email = str(record.get('email', '')).strip()
        if not email:
            skipped_no_email += 1
            continue
            
        # Check Duplicate
        if email.lower() in existing_emails:
            skipped_dupe += 1
            # Still add to DB list if valid, as DB might be empty
            # But wait, mapped lead generation happens below
            mapped = map_lead(record)
            all_valid_leads.append(mapped)
            continue
            
        # Map and Add
        mapped = map_lead(record)
        to_import.append(mapped)
        all_valid_leads.append(mapped)
        existing_emails.add(email.lower()) # Prevent dupes within the import batch itself

    # --- 4. Report and Execute ---
    
    print("\n" + "="*40)
    print("IMPORT ANALYSIS")
    print("="*40)
    print(f"Total Source Records: {len(source_records)}")
    print(f"Skipped (Invalid/Closed): {skipped_status}")
    print(f"Skipped (No Email): {skipped_no_email}")
    print(f"Skipped (GSheet Duplicates): {skipped_dupe}")
    print(f"New for GSheet: {len(to_import)}")
    print(f"Valid for DB Sync: {len(all_valid_leads)}")
    print("="*40)

    if not all_valid_leads:
        logger.info("No valid leads found.")
        return

    # Preview first 3
    print("\nPreview of first 3 records to import:")
    for item in to_import[:3]:
        print("-" * 20)
        print(json.dumps(item, indent=2))
    
    print("-" * 20 + "\n")

    if dry_run:
        logger.info("DRY RUN MODE: No changes made to target sheet or database.")
        logger.info("Run with --live to execute the import.")
    else:
        # 1. Write to Google Sheet (Backup/View)
        logger.info(f"WRITING {len(to_import)} ROWS TO GOOGLE SHEETS...")
        
        # Prepare list of lists for gspread append
        headers = [
            "email", "first_name", "last_name", "role", "school_name", 
            "domain", "state", "city", "phone", "status", 
            "email_1_sent_at", "email_2_sent_at", "sender_email", "notes"
        ]
        
        rows_to_append = []
        for item in to_import:
            row = [item.get(h, "") for h in headers]
            rows_to_append.append(row)
        
        chunk_size = 500
        for i in range(0, len(rows_to_append), chunk_size):
            chunk = rows_to_append[i:i + chunk_size]
            logger.info(f"Appending batch {i // chunk_size + 1} to Sheets...")
            target_sheet.append_rows(chunk)
            
        # 2. Write to SQLite (Production DB)
        if all_valid_leads:
            logger.info(f"INGESTING {len(all_valid_leads)} LEADS INTO CAMPAIGN.DB...")
            
            db_path = os.path.join(os.path.dirname(__file__), "mailreef_automation", "campaign.db")
            cm = ContactManager(database_path=db_path)
            
            # ContactManager handles duplicates via INSERT OR IGNORE
            added = cm.bulk_import_leads(all_valid_leads)
            logger.info(f"SUCCESS: Import complete. Added {added} new leads to database.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Import Outscraper Leads')
    parser.add_argument('--live', action='store_true', help='Perform actual import')
    args = parser.parse_args()
    
    run_import(dry_run=not args.live)
