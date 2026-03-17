import csv
import os
import json
import sys
import asyncio
from typing import Dict, List, Any
from pathlib import Path

# Add project root to sys.path
sys.path.append("/Users/mac/Ivybound")
sys.path.append("/Users/mac/Desktop/LeadMachine")

from sheets_integration import GoogleSheetsClient
from core.verifier import verify_email_bulk
from mailreef_automation.logger_util import get_logger

logger = get_logger("MASS_IMPORT_VERIFY")

FILES = [
    "/Users/mac/Downloads/22,000 Contacts Middle Schools.csv",
    "/Users/mac/Downloads/31,000 Contacts High Schools.csv"
]
# New file detected by the user
PASSED_PRE_VERIFIED_FILE = "/Users/mac/Downloads/contacts - Sheet1-passed.csv"

# Local caches of what we processed in standard runs
PASSED_LOG_LIST = "/Users/mac/Ivybound/already_verified_emails.txt"
FAILED_LOG_LIST = "/Users/mac/Ivybound/already_failed_emails.txt"

def load_processed_emails():
    processed = set()
    for f in [PASSED_LOG_LIST, FAILED_LOG_LIST]:
        if os.path.exists(f):
            with open(f, 'r') as fh:
                for line in fh:
                    processed.add(line.strip().lower())
    return processed

async def main():
    logger.info("Starting ENHANCED mass import and verification...")
    
    # 1. Setup Sheets Client
    client = GoogleSheetsClient(input_sheet_name='Ivy Bound - Campaign Leads')
    client.setup_sheets()
    
    # Load existing to avoid re-adding
    existing_records = client._fetch_all_records()
    existing_emails = {str(r.get('email', '')).lower().strip() for r in existing_records if r.get('email')}
    
    processed_emails = load_processed_emails()
    logger.info(f"Loaded {len(processed_emails)} emails already processed in previous log runs.")

    batch_to_write = []

    # 2. Process the "Pre-Verified" file (the 3294 leads)
    if os.path.exists(PASSED_PRE_VERIFIED_FILE):
        logger.info(f"Processing pre-verified file: {PASSED_PRE_VERIFIED_FILE}")
        with open(PASSED_PRE_VERIFIED_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            # Find which column is email
            header = next(reader)
            email_idx = 1 # Based on head output: website, email, phone...
            
            for row in reader:
                if len(row) < 2: continue
                email = row[email_idx].lower().strip()
                if not email or email in existing_emails:
                    continue
                
                # Simple extraction
                lead = {
                    "email": email,
                    "first_name": "", # Hard to parse from this format without more context
                    "last_name": "",
                    "role": "Principal / Director",
                    "school_name": row[0].replace('http://', '').replace('https://', '').replace('www.', '').split('/')[0],
                    "domain": row[0].replace('http://', '').replace('https://', '').replace('www.', '').split('/')[0],
                    "phone": row[2] if len(row) > 2 else "",
                    "school_type": "High School", # Default
                    "status": "pending",
                    "email_verified": "verified",
                    "notes": "Imported from pre-verified passed list"
                }
                batch_to_write.append(lead)
                existing_emails.add(email)
                
                if len(batch_to_write) >= 40:
                    logger.info(f"💾 Flushing {len(batch_to_write)} pre-verified leads...")
                    client.add_leads_batch(batch_to_write)
                    batch_to_write = []

    # 3. Process the 53k files (standard flow)
    new_leads_to_verify = []
    for f_path in FILES:
        stype = "Middle School" if "Middle" in f_path else "High School"
        logger.info(f"Parsing {f_path}...")
        with open(f_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get('email', '').lower().strip()
                if not email or email in existing_emails:
                    continue
                
                # Format name
                full_name = row.get('full_name', '')
                parts = full_name.split()
                first = parts[0] if parts else ""
                last = " ".join(parts[1:]) if len(parts) > 1 else ""
                
                lead = {
                    "email": email,
                    "first_name": first,
                    "last_name": last,
                    "role": row.get('title') or row.get('level') or "Principal / Director",
                    "school_name": row.get('company_domain', '').replace('http://', '').replace('https://', '').replace('www.', '').split('/')[0],
                    "domain": row.get('company_domain', '').replace('http://', '').replace('https://', '').replace('www.', '').split('/')[0],
                    "phone": row.get('phone', ''),
                    "school_type": stype,
                    "status": "pending",
                    "email_verified": "verified",
                    "notes": f"Imported from mass contact list {os.path.basename(f_path)}"
                }
                
                # Cache skip logic
                if email in processed_emails:
                    # Check if it was a PASS
                    with open(PASSED_LOG_LIST, 'r') as pf:
                        if email in pf.read().lower():
                            batch_to_write.append(lead)
                    continue

                new_leads_to_verify.append(lead)
                existing_emails.add(email)

    # 4. Final verification loop
    logger.info(f"Total leads remaining to verify via API: {len(new_leads_to_verify)}")
    
    passed_emails_list = []
    failed_emails_list = []

    for i, lead in enumerate(new_leads_to_verify):
        email = lead['email']
        logger.info(f"[{i+1}/{len(new_leads_to_verify)}] Verifying {email}...")
        try:
            v_result = await verify_email_bulk(email)
            if v_result.get('valid'):
                logger.info(f"  ✅ PASSED")
                batch_to_write.append(lead)
                passed_emails_list.append(email)
            else:
                logger.info(f"  ❌ FAILED: {v_result.get('reason')}")
                failed_emails_list.append(email)
        except Exception as e:
            logger.error(f"  ⚠️ Error: {e}")
            if "Out of Credits" in str(e): break

        if len(batch_to_write) >= 20:
            if client.add_leads_batch(batch_to_write):
                with open(PASSED_LOG_LIST, 'a') as pf:
                    for e in passed_emails_list: pf.write(f"{e}\n")
                with open(FAILED_LOG_LIST, 'a') as ff:
                    for e in failed_emails_list: ff.write(f"{e}\n")
                batch_to_write = []
                passed_emails_list = []
                failed_emails_list = []

    if batch_to_write:
        client.add_leads_batch(batch_to_write)

if __name__ == "__main__":
    asyncio.run(main())
