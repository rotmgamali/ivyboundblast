from sheets_integration import GoogleSheetsClient

SHEET_NAME = "Ivy Bound - Campaign Leads"

def check_round_2():
    print(f"Checking Round 2 status in '{SHEET_NAME}'...")
    sheets = GoogleSheetsClient(input_sheet_name=SHEET_NAME)
    sheets.setup_sheets()
    
    records = sheets.input_sheet.sheet1.get_all_records()
    
    total_leads = len(records)
    round_1_sent = 0
    round_2_sent = 0
    replied = 0
    
    for r in records:
        status = str(r.get("status", "")).lower()
        if status == "replied":
            replied += 1
            
        if r.get("email_1_sent_at"):
            round_1_sent += 1
            
        if r.get("email_2_sent_at"):
            round_2_sent += 1
            
    print(f"\n==========================================")
    print(f"📊 CAMPAIGN STATUS: IVYBOUND")
    print(f"👥 Total Leads: {total_leads}")
    print(f"📧 Round 1 Sent: {round_1_sent}")
    print(f"📩 Round 2 Sent: {round_2_sent}")
    print(f"💬 Replied: {replied}")
    print(f"==========================================\n")

if __name__ == "__main__":
    check_round_2()
