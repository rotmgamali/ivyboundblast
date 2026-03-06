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
logger = logging.getLogger("RECOVERY_AUDIT")

def main():
    logger.info("🚀 Starting Exhaustive Historical Recovery Audit...")
    
    # 1. Initialize Clients
    sheets = GoogleSheetsClient()
    sheets.setup_sheets()
    
    # We use ReplyWatcher's permissive filtering
    watcher = ReplyWatcher(profile_name="IVYBOUND")
    mailreef = watcher.mailreef
    
    # 2. Fetch Existing Tracking Data to prevent duplicates
    logger.info("📋 Fetching existing tracking data...")
    tracking_records = sheets.replies_sheet.sheet1.get_all_records()
    
    # Create a unique key for each already tracked message
    # We combine email + subject + date snippet to be safe
    tracked_keys = set()
    for r in tracking_records:
        email = str(r.get('From Email', '')).lower().strip()
        subject = str(r.get('Subject', '')).lower().strip()
        # Keep it simple: email + subject
        if email and subject:
            tracked_keys.add(f"{email}|{subject}")

    # 3. Fetch ALL Inbound Messages from Mailreef (Historical Scan)
    all_messages = []
    page = 1
    max_pages = 50 # Mailreef usually keeps 30-60 days of history
    
    logger.info(f"📡 Scanning up to {max_pages} pages of history...")
    
    while page <= max_pages:
        logger.info(f"  Fetching page {page}...")
        try:
            res = mailreef.get_global_inbound(page=page, display=100)
            batch = res.get("data", [])
            if not batch:
                logger.info("  No more messages found.")
                break
            
            all_messages.extend(batch)
            if len(batch) < 100:
                break
            page += 1
            time.sleep(1) # Rate limit friendliness
        except Exception as e:
            logger.error(f"  Error on page {page}: {e}")
            break

    logger.info(f"✓ Scanned {len(all_messages)} total inbound messages.")

    # 4. Identify Missing Replies
    missing_replies = []
    logger.info("🔍 Analyzing messages for high-confidence lead indicators...")
    
    # Ivy Bound Specific Keywords for content matching
    ivy_keywords = ["ivy bound", "sat", "act", "mark greenstein", "test prep", "scholarship", "scholarships"]
    
    for msg in all_messages:
        from_email = str(msg.get("from_email", "")).lower().strip()
        subject = str(msg.get("subject_line", "")).lower().strip()
        snippet = str(msg.get("snippet_preview", "")).lower()
        
        # --- LEAD INDICATOR LOGIC ---
        is_lead_recovery = False
        
        # 1. Known Lead Email
        if from_email in watcher.lead_emails:
            is_lead_recovery = True
            reason = "Direct Email Match"
        
        # 2. Known Lead Domain (Non-generic)
        if not is_lead_recovery and '@' in from_email:
            domain = from_email.split('@')[-1]
            if domain in watcher.lead_domains:
                is_lead_recovery = True
                reason = "Domain Match"
        
        # 3. Subject Line Fragment (Indicates thread reply)
        if not is_lead_recovery:
            known_fragments = ["quick question", "supporting families", "boosting enrollment", 
                               "academic outcomes", "differentiation", "merit scholarship",
                               "college readiness", "student-athletes", "test prep", 
                               "enhancing value", "enrollment value"]
            if any(frag in subject for frag in known_fragments):
                is_lead_recovery = True
                reason = "Campaign Subject Match"
        
        # 4. Content Keyword Match
        if not is_lead_recovery:
            if any(kw in snippet for kw in ivy_keywords) or any(kw in subject for kw in ivy_keywords):
                is_lead_recovery = True
                reason = "Keyword Match (Ivy Bound/SAT/etc)"

        # --- FINAL FILTER ---
        if not is_lead_recovery:
            continue
            
        # EXTRA PRECISION: Skip if it matches warmup patterns even if reason found
        if watcher.is_warmup(from_email, subject):
            logger.info(f"  [SKIP] Filtered as warmup (Recovery): {from_email} | {subject}")
            continue
            
        # B. Duplicate check
        key = f"{from_email}|{subject.strip()}"
        if key in tracked_keys:
            continue
            
        # C. It is a missing lead-related reply!
        ts = msg.get("ts")
        msg_dt = datetime.fromtimestamp(ts) if ts else datetime.now()
        
        # Normalize for log_reply
        body_text = msg.get("body_text")
        if not body_text and msg.get("body_html"):
            import re
            body_text = re.sub('<[^<]+?>', '', msg.get("body_html"))
            
        reply_data = {
            'received_at': msg_dt.isoformat(),
            'from_email': from_email,
            'subject': subject,
            'snippet': body_text if body_text else msg.get("snippet_preview", ""),
            'original_sender': msg.get("to")[0] if msg.get("to") else "unknown",
            'notes': f"RECOVERED: {reason}"
        }
        missing_replies.append(reply_data)

    logger.info(f"💡 Found {len(missing_replies)} missing replies to recover.")

    # 5. Log Missing Replies
    if missing_replies:
        logger.info(f"✍️ Recovery started: Pushing {len(missing_replies)} replies to Google Sheets...")
        for i, reply in enumerate(missing_replies):
            try:
                # This call handles enrichment (email/domain/subject matching)
                # and status updates automatically
                sheets.log_reply(reply)
                logger.info(f"  [{i+1}/{len(missing_replies)}] Recovered: {reply['from_email']}")
                time.sleep(1) # Avoid Google Sheets quota issues
            except Exception as e:
                logger.error(f"  Failed to recover {reply['from_email']}: {e}")
    else:
        logger.info("✅ No missing replies found. Everything is already tracked!")

    logger.info("🏁 Recovery Audit Complete.")

if __name__ == "__main__":
    main()
