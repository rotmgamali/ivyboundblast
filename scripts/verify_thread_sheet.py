import gspread
from google.oauth2 import service_account
import os
import json

def verify_sheet():
    cred_file = "/Users/mac/Desktop/Ivybound/credentials/service_account.json"
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = service_account.Credentials.from_service_account_file(cred_file, scopes=scopes)
    gc = gspread.authorize(creds)
    
    sheet = gc.open("Ivy Bound - Reply Tracking").sheet1
    rows = sheet.get_all_values()
    
    print(f"Header: {rows[0]}")
    for i, row in enumerate(rows[1:6]):
        print(f"\nRow {i+1}:")
        print(f"From: {row[1]}")
        print(f"Thread Length: {len(row[6])}")
        print(f"Thread Content Snippet: {row[6][:500]}")

if __name__ == "__main__":
    verify_sheet()
