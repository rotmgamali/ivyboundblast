from sheets_integration import GoogleSheetsClient
import logging

logging.basicConfig(level=logging.INFO)

def test_profile(profile_name):
    print(f"\n--- Testing Profile: {profile_name} ---")
    try:
        from mailreef_automation import automation_config
        config = automation_config.CAMPAIGN_PROFILES[profile_name]
        
        client = GoogleSheetsClient(
            input_sheet_name=config["input_sheet"],
            replies_sheet_name=config["replies_sheet"]
        )
        client.setup_sheets()
        print(f"✅ Successfully connected to {profile_name} sheets!")
    except Exception as e:
        print(f"❌ Failed to connect to {profile_name} sheets: {e}")

if __name__ == "__main__":
    test_profile("IVYBOUND")
    test_profile("WEB4GURU_ACCOUNTANTS")
