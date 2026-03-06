import os
import sys
import json
import gspread
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

TOKEN_FILE = os.path.join(ROOT_DIR, 'credentials', 'token.json')
SERVICE_ACCOUNT_EMAIL = "ide-207@citric-pager-402923.iam.gserviceaccount.com"

# Scopes used in regular sheets_integration.py
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.readonly'
]

def test_user_token():
    if not os.path.exists(TOKEN_FILE):
        print(f"Error: {TOKEN_FILE} not found.")
        return

    with open(TOKEN_FILE, 'r') as f:
        creds_data = json.load(f)
    
    creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
    
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            print("Token expired, refreshing...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Failed to refresh token: {e}")
                return
        else:
            print("Token invalid and cannot be refreshed.")
            return

    client = gspread.authorize(creds)
    
    print("User authenticated successfully via token.json.")
    print("\nAttempting to list spreadsheets owned by user...")
    
    try:
        sheets = client.openall()
        if sheets:
            for s in sheets:
                print(f" - Found: {s.title} (ID: {s.id})")
        else:
            print(" No spreadsheets found with current token scopes.")
    except Exception as e:
        print(f"Error listing sheets: {e}")

if __name__ == "__main__":
    test_user_token()
