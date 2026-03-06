
import sys
import os
from datetime import datetime
from collections import Counter
import pandas as pd

# Add project root and automation dir to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "mailreef_automation"))

from sheets_integration import GoogleSheetsClient

def calculate_average():
    print("📡 Connecting to Google Sheets...")
    client = GoogleSheetsClient()
    client.setup_sheets()
    
    print("📡 Fetching all records from Campaign Leads sheet...")
    records = client._fetch_all_records()
    print(f"✅ Total Records: {len(records)}")
    
    dates = []
    
    for r in records:
        # Check both Email 1 and Email 2 sent dates
        e1_at = r.get('email_1_sent_at')
        if e1_at:
            try:
                # ISO format or YYYY-MM-DD
                dt = datetime.fromisoformat(e1_at.split('T')[0])
                dates.append(dt.date())
            except (ValueError, AttributeError):
                pass
                
        e2_at = r.get('email_2_sent_at')
        if e2_at:
            try:
                dt = datetime.fromisoformat(e2_at.split('T')[0])
                dates.append(dt.date())
            except (ValueError, AttributeError):
                pass
    
    if not dates:
        print("❌ No sent dates found.")
        return

    # Count sends per day
    daily_sends = Counter(dates)
    
    # Create a DataFrame for easier analysis
    df = pd.DataFrame.from_dict(daily_sends, orient='index', columns=['count']).sort_index()
    
    print("\n--- Sending Volume per Day ---")
    print(df)
    
    total_days = len(df)
    total_sends = df['count'].sum()
    average_per_day = total_sends / total_days
    
    print(f"\n--- Statistics ---")
    print(f"Period: {df.index.min()} to {df.index.max()}")
    print(f"Total Days with Activity: {total_days}")
    print(f"Total Emails Sent: {total_sends}")
    print(f"📈 AVERAGE EMAILS PER DAY: {average_per_day:.2f}")

if __name__ == "__main__":
    calculate_average()
