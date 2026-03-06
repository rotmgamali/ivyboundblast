#!/usr/bin/env python3
import os
import json
import logging
import time
from datetime import datetime
from typing import List, Dict, Set
from mailreef_automation.mailreef_client import MailreefClient
from sheets_integration import GoogleSheetsClient
from reply_watcher import ReplyWatcher

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("COMPLETE_AUDIT")

def main():
    logger.info("🚀 Starting Complete Inbound Audit Export...")
    
    # 1. Initialize Clients
    sheets = GoogleSheetsClient()
    sheets.setup_sheets()
    
    # We use ReplyWatcher's is_warmup logic
    watcher = ReplyWatcher(profile_name="IVYBOUND")
    mailreef = watcher.mailreef
    
    # 2. Fetch Data for Cross-Referencing
    logger.info("📋 Fetching lead data for cross-referencing...")
    leads_records = sheets.input_sheet.sheet1.get_all_records()
    lead_emails = {str(r.get('email', '')).lower().strip() for r in leads_records if r.get('email')}
    
    logger.info("📋 Fetching existing tracking data...")
    tracking_records = sheets.replies_sheet.sheet1.get_all_records()
    tracked_emails = {str(r.get('From Email', '')).lower().strip() for r in tracking_records if r.get('From Email')}
    tracked_subjects = {str(r.get('Subject', '')).lower().strip() for r in tracking_records if r.get('Subject')}

    # 3. Create/Prepare Audit Spreadsheet
    audit_sheet_name = "Ivy Bound - Complete Audit"
    try:
        audit_ss = sheets.client.open(audit_sheet_name)
        logger.info(f"✓ Found existing audit sheet: {audit_sheet_name}")
    except:
        audit_ss = sheets.client.create(audit_sheet_name)
        logger.info(f"✓ Created new audit sheet: {audit_sheet_name}")

    worksheet = audit_ss.sheet1
    worksheet.clear()
    headers = [
        "Date", 
        "From Email", 
        "Subject", 
        "Snippet", 
        "Filter Decision", 
        "Is Lead?", 
        "Already Tracked?", 
        "Original Inbox"
    ]
    worksheet.append_row(headers)
    
    # 4. Fetch ALL Inbound Messages from Mailreef
    all_messages = []
    page = 1
    logger.info("📡 Fetching ALL inbound messages from Mailreef...")
    while True:
        logger.info(f"  Fetching page {page}...")
        res = mailreef.get_global_inbound(page=page, display=100)
        batch = res.get("data", [])
        if not batch:
            break
        all_messages.extend(batch)
        if len(batch) < 100 or page >= 10: # Limit to 1000 messages for safety
            break
        page += 1
        time.sleep(1)

    logger.info(f"✓ Fetched {len(all_messages)} total messages.")

    # 5. Process and Write
    rows_to_append = []
    for msg in all_messages:
        from_email = str(msg.get("from_email", "")).lower().strip()
        subject = msg.get("subject_line", "")
        
        # Filter Decision
        is_warmup = watcher.is_warmup(from_email, subject)
        decision = "Warming" if is_warmup else "IvyBound / Real Reply"
        
        # Lead Check
        is_lead = "Yes" if from_email in lead_emails else "No"
        
        # Tracking Check
        # Check by email OR if it was already tracked (using subject/email combo if possible)
        already_tracked = "No"
        if from_email in tracked_emails:
            already_tracked = "Yes"
        
        # Formatting rows
        ts = msg.get("ts")
        date_str = datetime.fromtimestamp(ts).isoformat() if ts else "Unknown"
        snippet = msg.get("snippet_preview", "")[:500]
        inbox = msg.get("to")[0] if msg.get("to") else "unknown"
        
        rows_to_append.append([
            date_str,
            from_email,
            subject,
            snippet,
            decision,
            is_lead,
            already_tracked,
            inbox
        ])

    # Batch append in chunks of 100
    logger.info(f"✍️ Writing {len(rows_to_append)} rows to spreadsheet...")
    for i in range(0, len(rows_to_append), 100):
        chunk = rows_to_append[i:i+100]
        worksheet.append_rows(chunk)
        logger.info(f"  Wrote rows {i+1} to {min(i+100, len(rows_to_append))}...")
        time.sleep(1)

    # 6. Formatting
    worksheet.freeze(rows=1)
    worksheet.format("A1:H1", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}})
    
    logger.info(f"✅ Audit complete! Spreadsheet available at: {audit_ss.url}")

if __name__ == "__main__":
    main()
