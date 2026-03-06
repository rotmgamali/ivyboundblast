from sheets_integration import GoogleSheetsClient
import gspread
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SOURCE_SHEET_NAME = "Outscraper-20260201101100m30"
DEST_SHEET_NAME = "Ivy Bound - Campaign Leads"
# Based on headers: A=Email, B=First, C=Last
# We will update B2:C<End>

def fix_names():
    client = GoogleSheetsClient()
    gc = client.client
    
    print(f"Opening Source: {SOURCE_SHEET_NAME}...")
    source_sheet = gc.open(SOURCE_SHEET_NAME).sheet1
    print("Reading ALL source records (this may take a moment)...")
    source_records = source_sheet.get_all_records()
    print(f"Loaded {len(source_records)} source records.")
    
    # Build Map: Email -> {first_name, last_name}
    # Normalize email to lower case
    source_map = {}
    for r in source_records:
        email = str(r.get('email', '')).strip().lower()
        if email:
            # Prefer 'first_name' column, fallback to 'name' split if needed?
            # User said "first_name" column exists and has data.
            source_map[email] = {
                'first': r.get('first_name', ''),
                'last': r.get('last_name', '')
            }
            
    print(f"Built map for {len(source_map)} emails.")
    
    print(f"Opening Dest: {DEST_SHEET_NAME}...")
    dest_sheet = gc.open(DEST_SHEET_NAME).sheet1
    print("Reading Dest records to preserve order...")
    # get_all_records might verify headers, but we just want the email column to match logic?
    # Actually get_all_records is good.
    dest_records = dest_sheet.get_all_records()
    print(f"Loaded {len(dest_records)} dest records.")
    
    updates = [] # List of [First, Last]
    
    update_count = 0
    match_count = 0
    
    for r in dest_records:
        email = str(r.get('email', '')).strip().lower()
        
        # Default to existing if no match
        new_first = r.get('first_name', '')
        new_last = r.get('last_name', '')
        
        if email in source_map:
            src = source_map[email]
            match_count += 1
            
            # Check if likely garbage (Match first word of school)
            # Or just blindly overwrite because Source is "Truth"? 
            # User said "source spreadsheet" names are correct.
            # ALWAYS overwrite, even if source is empty (Empty is better than 'Harvest')
            
            # Update First Name
            if src['first'] != new_first:
                new_first = src['first']
                update_count += 1
            
            # Update Last Name
            if src['last'] != new_last:
                new_last = src['last']
                # We count updates per field or per row? Let's just update.

        updates.append([new_first, new_last])
        
    print(f"Matches found: {match_count}")
    print(f"Rows to be modified (different data): {update_count} (approx)")
    
    if update_count == 0:
        print("No changes needed!")
        return

    # PROMPT USER CONFIRMATION (Simulated here, but useful logic)
    # in an Agent, we just proceed if confident.
    
    print("Preparing Batch Update...")
    # Range is B2 : C(len(updates)+1)
    end_row = len(updates) + 1
    cell_range = f"B2:C{end_row}"
    
    print(f"Updating range {cell_range} with {len(updates)} rows...")
    dest_sheet.update(cell_range, updates)
    print("✅ SUCCESS: Bulk updated names.")

if __name__ == "__main__":
    fix_names()
