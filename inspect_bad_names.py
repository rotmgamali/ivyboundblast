from sheets_integration import GoogleSheetsClient

SHEET_NAME = "Ivy Bound - Campaign Leads"

def inspect_names():
    print(f"Inspecting names in '{SHEET_NAME}'...")
    sheets = GoogleSheetsClient(input_sheet_name=SHEET_NAME)
    sheets.setup_sheets()
    
    records = sheets.input_sheet.sheet1.get_all_records()
    
    admin_count = 0
    names_found = {}
    
    for r in records:
        name = str(r.get("first_name", "")).strip()
        if not name: continue
        
        lower_name = name.lower()
        if "administrator" in lower_name:
            admin_count += 1
            names_found[name] = names_found.get(name, 0) + 1
            
    print(f"\n==========================================")
    print(f"📊 NAME INSPECTION: IVYBOUND")
    print(f"❌ Leads with 'Administrator' in name: {admin_count}")
    print(f"\nTop matches:")
    sorted_names = sorted(names_found.items(), key=lambda x: x[1], reverse=True)
    for name, count in sorted_names[:10]:
        print(f" - {name}: {count}")
    print(f"==========================================\n")

if __name__ == "__main__":
    inspect_names()
