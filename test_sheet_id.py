import os
import sys
import json
import gspread
from google.oauth2 import service_account

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

SERVICE_ACCOUNT_FILE = os.path.join(ROOT_DIR, 'credentials', 'service_account.json')
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.readonly'
]

def test_sheet_access(sheet_id):
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"Error: {SERVICE_ACCOUNT_FILE} not found.")
        return

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    client = gspread.authorize(creds)
    
    print(f"Service Account: {creds.service_account_email}")
    print(f"Attempting to open sheet by ID: {sheet_id}")
    
    try:
        sheet = client.open_by_key(sheet_id)
        print(f"✅ Success! Opened sheet: {sheet.title}")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_sheet_access(sys.argv[1])
    else:
        # The ID from the URL provided by the user
        test_sheet_access("1G7chSKGCdc4_uzbd2iPmHiwv0XxbRGtb11CmEKPhPQU")
