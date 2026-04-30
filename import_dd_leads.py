#!/usr/bin/env python3
"""
Import Demons & Deities scraped contacts into Google Sheets for the campaign.

Reads from: ~/Desktop/Demons And Deities/scripts/marketing/output/mega-crypto-contacts.csv
Writes to:  Google Sheet "Demons & Deities - Campaign Leads"

Usage:
    python import_dd_leads.py               # Import all contacts
    python import_dd_leads.py --dry-run     # Preview without writing
    python import_dd_leads.py --category investor  # Import only investors
"""

import csv
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "mailreef_automation"))

from sheets_integration import GoogleSheetsClient
from mailreef_automation.logger_util import get_logger

logger = get_logger("DD_IMPORT")

# Source file
DD_PROJECT = Path.home() / "Desktop" / "Demons And Deities"
CONTACTS_CSV = DD_PROJECT / "scripts" / "marketing" / "output" / "mega-crypto-contacts.csv"

# Sheet config matching automation_config.py
SHEET_NAME = "Demons & Deities - Campaign Leads"
REPLIES_SHEET = "Demons & Deities - Reply Tracking"

# Expected columns in the Google Sheet (matching Ivybound's format)
SHEET_HEADERS = [
    "email", "first_name", "last_name", "role", "school_name",
    "website", "city", "state", "status", "sent_at",
    "sender_email", "content", "custom_data"
]


def map_contact_to_lead(contact: dict) -> dict:
    """Map a scraped crypto contact to the Ivybound lead format."""
    name = contact.get("Name", "")

    # Try to split name into first/last
    parts = name.strip().split(" ", 1)
    first_name = parts[0] if parts else name
    last_name = parts[1] if len(parts) > 1 else ""

    # Map category to role (used for archetype matching)
    category = contact.get("Category", "general")
    subcategory = contact.get("Subcategory", "")
    role = subcategory if subcategory else category

    return {
        "email": contact.get("Email", "").strip(),
        "first_name": first_name,
        "last_name": last_name,
        "role": role,
        "school_name": name,  # Reuse school_name field for org/channel name
        "website": contact.get("URL", ""),
        "city": "",
        "state": "",
        "status": "pending",
        "sent_at": "",
        "sender_email": "",
        "content": "",
        "custom_data": f'{{"source": "{contact.get("Source", "")}", "platform": "{contact.get("Platform", "")}"}}'
    }


def load_contacts(csv_path: str, category_filter: str = None) -> list:
    """Load contacts from CSV and optionally filter by category."""
    contacts = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if category_filter and row.get("Category", "").lower() != category_filter.lower():
                continue
            contacts.append(row)

    return contacts


def main():
    parser = argparse.ArgumentParser(description="Import D&D leads to Google Sheets")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--category", type=str, help="Filter by category (influencer/investor/promoter)")
    parser.add_argument("--csv", type=str, default=str(CONTACTS_CSV), help="Path to contacts CSV")
    args = parser.parse_args()

    csv_path = args.csv

    if not os.path.exists(csv_path):
        logger.error(f"CSV not found: {csv_path}")
        sys.exit(1)

    # Load contacts
    contacts = load_contacts(csv_path, args.category)
    logger.info(f"Loaded {len(contacts)} contacts from {csv_path}")

    if args.category:
        logger.info(f"Filtered to category: {args.category}")

    # Map to lead format
    leads = [map_contact_to_lead(c) for c in contacts]

    # Deduplicate by email
    seen = set()
    unique_leads = []
    for lead in leads:
        email = lead["email"].lower()
        if email not in seen:
            seen.add(email)
            unique_leads.append(lead)

    logger.info(f"Unique leads after dedup: {len(unique_leads)}")

    if args.dry_run:
        print(f"\n{'='*60}")
        print(f"DRY RUN — Would import {len(unique_leads)} leads")
        print(f"{'='*60}\n")

        # Show breakdown by role/archetype
        by_role = {}
        for lead in unique_leads:
            role = lead["role"]
            by_role[role] = by_role.get(role, 0) + 1

        print("By category:")
        for role, count in sorted(by_role.items(), key=lambda x: -x[1]):
            print(f"  {role}: {count}")

        print(f"\nSample leads:")
        for lead in unique_leads[:10]:
            print(f"  {lead['email']:40s} [{lead['role']}] {lead['school_name']}")

        return

    # Connect to Google Sheets
    logger.info(f"Connecting to Google Sheet: {SHEET_NAME}")
    try:
        sheets = GoogleSheetsClient(
            input_sheet_name=SHEET_NAME,
            replies_sheet_name=REPLIES_SHEET
        )
        sheets.setup_sheets()
    except Exception as e:
        logger.error(f"Failed to connect to Sheets: {e}")
        logger.info("You may need to create the Google Sheet first:")
        logger.info(f'  1. Create a new Google Sheet named "{SHEET_NAME}"')
        logger.info(f'  2. Create a second sheet named "{REPLIES_SHEET}"')
        logger.info(f'  3. Share both with the service account email in credentials/service_account.json')
        logger.info(f'  4. Add headers to row 1: {", ".join(SHEET_HEADERS)}')
        sys.exit(1)

    # Check if sheet has headers
    try:
        worksheet = sheets.input_sheet.sheet1
        existing = worksheet.get_all_values()

        if not existing or existing[0] != SHEET_HEADERS:
            logger.info("Setting up headers...")
            worksheet.update('A1', [SHEET_HEADERS])
    except Exception as e:
        logger.error(f"Error checking headers: {e}")

    # Get existing emails to avoid duplicates
    try:
        all_records = worksheet.get_all_records()
        existing_emails = {r.get("email", "").lower() for r in all_records}
        logger.info(f"Found {len(existing_emails)} existing leads in sheet")
    except:
        existing_emails = set()

    # Filter out already-imported leads
    new_leads = [l for l in unique_leads if l["email"].lower() not in existing_emails]
    logger.info(f"New leads to import: {len(new_leads)} (skipping {len(unique_leads) - len(new_leads)} already in sheet)")

    if not new_leads:
        logger.info("No new leads to import!")
        return

    # Batch write to sheet (gspread supports batch append)
    rows = []
    for lead in new_leads:
        rows.append([lead[h] for h in SHEET_HEADERS])

    # Append in batches of 100 to avoid API limits
    batch_size = 100
    imported = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        try:
            worksheet.append_rows(batch, value_input_option='RAW')
            imported += len(batch)
            logger.info(f"Imported {imported}/{len(rows)} leads...")
        except Exception as e:
            logger.error(f"Error importing batch {i}: {e}")
            import time
            time.sleep(10)  # Back off on rate limit
            try:
                worksheet.append_rows(batch, value_input_option='RAW')
                imported += len(batch)
            except:
                logger.error(f"Failed again, skipping batch {i}")

    print(f"\n{'='*60}")
    print(f"IMPORT COMPLETE: {imported} leads added to '{SHEET_NAME}'")
    print(f"{'='*60}")
    print(f"\nTo start sending:")
    print(f"  cd /Users/mac/Ivybound")
    print(f"  python mailreef_automation/main.py --profile DEMONS_AND_DEITIES")


if __name__ == "__main__":
    main()
