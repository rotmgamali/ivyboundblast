from sheets_integration import GoogleSheetsClient
import logging

logging.basicConfig(level=logging.INFO)

def clear_sheet():
    print("🧹 Wiping 'Ivy Bound - Scraped Leads' sheet to remove inaccurate names...")
    try:
        sheets = GoogleSheetsClient()
        sheets.setup_sheets()
        success = sheets.clear_input_sheet()
        if success:
            print("✅ Sheet cleared successfully. Ready for fresh accurately-named data.")
        else:
            print("❌ Failed to clear sheet.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    clear_sheet()
