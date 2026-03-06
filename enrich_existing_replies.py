from sheets_integration import GoogleSheetsClient
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ENRICHER")

PROFILES = ["IVYBOUND", "STRATEGY_B"]

def enrich_sheets():
    for profile in PROFILES:
        import mailreef_automation.automation_config as config
        c = config.CAMPAIGN_PROFILES[profile]
        
        logger.info(f"🚀 Enriching {profile} tracking sheet: {c['replies_sheet']}...")
        sheets = GoogleSheetsClient(
            input_sheet_name=c['input_sheet'],
            replies_sheet_name=c['replies_sheet']
        )
        sheets.setup_sheets()
        
        # Force fetch all records from leads for lookup
        sheets._fetch_all_records()
        
        replies_sheet = sheets.replies_sheet.sheet1
        records = replies_sheet.get_all_records()
        
        headers = replies_sheet.row_values(1)
        # Find indices (1-indexed for gspread)
        try:
            email_idx = headers.index('From Email') + 1
            school_idx = headers.index('School Name') + 1
            role_idx = headers.index('Role') + 1
        except ValueError:
            logger.error(f" Headers mismatch in {profile}. Skipping.")
            continue

        updates = []
        for i, r in enumerate(records, start=2):
            email = str(r.get('From Email', '')).lower().strip()
            school = r.get('School Name', '')
            role = r.get('Role', '')
            
            if not school or not role:
                lead = sheets._cache.get(email)
                if lead:
                    new_school = school or lead.get('school_name', '')
                    new_role = role or lead.get('role', '')
                    
                    if new_school != school:
                        updates.append({'range': f'{chr(64+school_idx)}{i}', 'values': [[new_school]]})
                    if new_role != role:
                        updates.append({'range': f'{chr(64+role_idx)}{i}', 'values': [[new_role]]})
        
        if updates:
            logger.info(f"  Enriching {len(updates)} cells...")
            # batch_update needs a list of cell update dicts
            replies_sheet.batch_update(updates)
            logger.info(f"  ✓ {profile} enrichment complete.")
        else:
            logger.info(f"  ✓ No enrichment needed for {profile}.")
            
        # Re-apply formatting for good measure
        sheets.apply_formatting()

if __name__ == "__main__":
    enrich_sheets()
