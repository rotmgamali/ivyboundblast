from reply_watcher import ReplyWatcher
from mailreef_automation.mailreef_client import MailreefClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

MISSING_EMAILS = [
    "jonathanrobertson@sudanisd.net",
    "mary@woodlandministries.com",
    "fedamorton@gmail.com",
    "leonschram@johnpauliihs.org",
    "michellep@stdominicsaviousv.org",
    "jessiejohns8@gmail.com",
    "apcecheryl@gmail.com",
    "matt@pixelspread.com",
    "stjohnacademyoffice@gmail.com",
    "h.barrera@scpetersantacruz.com",
    "p.carrol@scpetersantacruz.com",
    "b.jones@scpetersantacruz.com"
]

def repair_replies():
    print(f"🔧 Starting repair for {len(MISSING_EMAILS)} missing replies...")
    
    # Initialize components
    watcher = ReplyWatcher(profile_name="IVYBOUND")
    client = MailreefClient(api_key=os.getenv("MAILREEF_API_KEY"))
    
    # Fetch all inbound to find the actual message objects for these emails
    print("📡 Fetching Mailreef inbox to locate message data...")
    found_messages = []
    page = 1
    while len(found_messages) < len(MISSING_EMAILS) and page < 10:
        result = client.get_global_inbound(page=page, display=100)
        batch = result.get("data", [])
        if not batch: break
        
        for msg in batch:
            from_email = str(msg.get("from_email", "")).lower()
            if from_email in MISSING_EMAILS:
                # Normalize just like ReplyWatcher.get_inbox_replies
                body_text = msg.get("body_text")
                if not body_text and msg.get("body_html"):
                    import re
                    body_text = re.sub('<[^<]+?>', '', msg.get("body_html"))
                
                msg["body"] = body_text if body_text else msg.get("snippet_preview", "")
                msg["subject"] = msg.get("subject_line", "")
                msg["date"] = datetime.fromtimestamp(msg.get("ts", 0)).isoformat() if msg.get("ts") else datetime.now().isoformat()
                msg["inbox_email"] = msg.get("to")[0] if msg.get("to") else "unknown"
                
                found_messages.append(msg)
                # Remove from list once found so we don't pick up duplicates
                MISSING_EMAILS.remove(from_email)
        
        page += 1

    print(f"✅ Found data for {len(found_messages)} messages. Logging to sheets...")
    
    for msg in found_messages:
        from_email = msg.get('from_email')
        body = msg.get('body', '')
        subject = msg.get('subject', '')
        
        print(f"  Logging reply from {from_email}...")
        
        sentiment = watcher.analyze_sentiment(body)
        
        reply_data = {
            'received_at': msg.get('date'),
            'from_email': from_email,
            'subject': subject,
            'snippet': body,
            'sentiment': sentiment,
            'original_sender': msg.get('inbox_email'),
            'thread_id': msg.get('thread_id', msg.get('conversation_id'))
        }
        
        try:
            watcher.sheets_client.log_reply(reply_data)
            print(f"    ✓ Success ({sentiment})")
        except Exception as e:
            print(f"    ❌ Failed: {e}")

if __name__ == "__main__":
    repair_replies()
