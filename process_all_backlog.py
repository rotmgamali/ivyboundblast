
import sys
import os
import time
from datetime import datetime

# Add project root and automation dir to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "mailreef_automation"))

from reply_watcher import ReplyWatcher
from mailreef_automation.logger_util import get_logger

logger = get_logger("BACKLOG_PROCESSOR")

def process_full_backlog(clear_first=False):
    # We use a temporary lock name so we don't collide with the daemon watcher
    # BUT we should actually stop the watcher temporarily to avoid double-processing
    # Actually, log_reply is usually idempotent if handled correctly, but better safe.
    
    watcher = ReplyWatcher()
    watcher.sheets_client.setup_sheets() # CRITICAL FIX: Initialize sheet connections
    
    if clear_first:
        print("🧹 Clearing replies sheet for fresh run...")
        watcher.sheets_client.clear_replies()

    print("🚀 Starting FULL BACKLOG process (807+ emails expected)...")
    
    page = 1
    display = 100
    total_processed = 0
    
    while True:
        print(f"📄 Fetching page {page}...")
        result = watcher.mailreef.get_global_inbound(page=page, display=display)
        batch = result.get("data", [])
        total_count = result.get("total_count", 0)
        
        if not batch:
            print("Done! No more messages found.", flush=True)
            break
            
        print(f"📥 Processing {len(batch)} messages from page {page}...", flush=True)
        
        for msg in batch:
            # Re-normalize as in reply_watcher.py
            from_email = msg.get("from_email")
            
            # 1. Try body_text (full), 2. Try body_html (stripped), 3. Snippet
            body_text = msg.get("body_text")
            if not body_text and msg.get("body_html"):
                import re
                body_text = re.sub('<[^<]+?>', '', msg.get("body_html"))
                
            body = body_text if body_text else msg.get("snippet_preview", "")
            subject = msg.get("subject_line", "")
            
            # FILTER: Skip warmup emails
            if watcher.is_warmup(subject):
                print(f"⏩ Skipping warmup: {subject}")
                continue

            ts = msg.get("ts")
            msg_dt = datetime.fromtimestamp(ts) if ts else datetime.now()
            
            # 1. Sentiment
            sentiment = watcher.analyze_sentiment(body)
            
            # 2. Update Sheets
            reply_data = {
                'received_at': msg_dt.isoformat(),
                'from_email': from_email,
                'subject': subject,
                'snippet': body,
                'sentiment': sentiment,
                'original_sender': msg.get("to")[0] if msg.get("to") else "unknown",
                'thread_id': msg.get('message_id')
            }
            
            try:
                # log_reply in sheets_integration handles the check/append
                watcher.sheets_client.log_reply(reply_data)
                total_processed += 1
                if total_processed % 10 == 0:
                    print(f"✅ Processed {total_processed}/{total_count}...")
            except Exception as e:
                print(f"❌ Error logging {from_email}: {e}")
        
        if len(batch) < display:
            print("Reached the end of the history.")
            break
            
        page += 1
        # Brief sleep for rate limiting
        time.sleep(1)

    print(f"\n🏁 FINISHED. Total processed: {total_processed}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear-sheet", action="store_true", help="Clear the replies sheet before starting")
    args = parser.parse_args()

    # We'll skip the singleton check for this manual script or use a different ID
    import lock_util
    try:
        lock_util.ensure_singleton('backlog_run')
        process_full_backlog(clear_first=args.clear_sheet)
    finally:
        lock_util.release_lock('backlog_run')
