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

def list_sheets():
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"Error: {SERVICE_ACCOUNT_FILE} not found.")
        return

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    client = gspread.authorize(creds)
    
    print(f"Service Account: {creds.service_account_email}")
    print("\nAvailable Spreadsheets:")
    titles = [s.title for s in client.openall()]
    if titles:
        for t in titles:
            print(f" - {t}")
    else:
        print(" (No spreadsheets found)")

if __name__ == "__main__":
    list_sheets()
