from sheets_integration import GoogleSheetsClient
from generators.email_generator import EmailGenerator
import os
from dotenv import load_dotenv

load_dotenv()

def show_examples():
    sheets = GoogleSheetsClient()
    sheets.setup_sheets()
    records = sheets.input_sheet.sheet1.get_all_records()
    
    r2_leads = [r for r in records if r.get('email_2_sent_at')][:2]
    
    if not r2_leads:
        # Fallback: just pick some leads that have email_1_sent
        r2_leads = [r for r in records if r.get('email_1_sent_at')][:2]
        print("Note: Showing what R2 WOULD look like for these leads (none found with R2 sent in this batch).")

    generator = EmailGenerator(templates_dir="templates")
    
    for i, lead in enumerate(r2_leads, 1):
        print(f"\n--- EXAMPLE {i} ({lead.get('email')}) ---")
        result = generator.generate_email(
            campaign_type="school",
            sequence_number=2,
            lead_data=lead,
            enrichment_data={}, # live scrape optional
            sender_email="outreach@aspireteam.space"
        )
        print(f"Subject: {result['subject']}")
        print(f"Body:\n{result['body']}")
        print("-" * 40)

if __name__ == "__main__":
    show_examples()
