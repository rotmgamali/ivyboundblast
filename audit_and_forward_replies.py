#!/usr/bin/env python3
"""
Reply Audit & Forward Script
-----------------------------
1. Scans ALL inbound Mailreef messages (past 7 days)
2. Identifies real school replies using lead-first matching
3. Categorizes each as ACTIONABLE (positive/neutral) or NOT ACTIONABLE (negative/spam)
4. Logs to the Ivy Bound - Reply Tracking sheet with:
   - Green highlight for actionable
   - Grey highlight for not actionable
   - Most recent at the top
5. Forwards every real reply to andrew@web4guru.com and cja@ivybound.net
"""
import os, sys, re, json, time
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "mailreef_automation"))
sys.path.insert(0, BASE_DIR)

from mailreef_automation.mailreef_client import MailreefClient
from mailreef_automation.telegram_alert import TelegramNotifier
import mailreef_automation.automation_config as config
from sheets_integration import GoogleSheetsClient
from generators.email_generator import EmailGenerator
from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, '.env'))
MAILREEF_API_KEY = os.getenv("MAILREEF_API_KEY")

# Forward all real replies to these addresses
FORWARD_TO = ["andrew@web4guru.com", "cja@ivybound.net"]
# Use any active inbox for forwarding
FORWARD_FROM_INBOX = None  # Will be set from first available inbox

PROFILE = "IVYBOUND"
profile_config = config.CAMPAIGN_PROFILES[PROFILE]

GENERIC_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com',
    'aol.com', 'msn.com', 'live.com', 'protonmail.com', 'me.com', 'comcast.net'
}

# Warmup patterns (bot noise)
WARMUP_PATTERNS = [
    "bug fixes", "software training", "expense reports",
    "sales report", "performance reviews",
    "volunteer day", "vendor negotiations", "health benefits",
    "team building", "intern welcome",
    "strategic planning", "remote work", "client meeting",
    "project update", "policy reminder", "office move",
    "company picnic", "birthday celebration", "quarterly goals",
    "tax compliance", "w-8ben", "documentation notice", "productivity tips",
    "celebration planning", "management system update", "achievement recognition",
    "maintenance notice", "hr policies", "marketing strategies",
    "training session", "retreat planning", "improvement suggestions",
    "challenge discussion", "publication discussion", "contact person",
    "new hire", "it support", "leave request", "w-8", "tax forms",
    "security update", "account action", "mandatory account",
    "office recycling", "employee satisfaction", "project timeline"
]


def main():
    print("=" * 60)
    print("📬 REPLY AUDIT & FORWARD SYSTEM")
    print("=" * 60)
    
    # Init clients
    mailreef = MailreefClient(api_key=MAILREEF_API_KEY)
    sheets = GoogleSheetsClient(
        input_sheet_name=profile_config["input_sheet"],
        replies_sheet_name=profile_config["replies_sheet"],
        replies_sheet_id=profile_config.get("replies_sheet_id")
    )
    sheets.setup_sheets()
    telegram = TelegramNotifier()
    generator = EmailGenerator()
    
    # Get inbox for forwarding
    try:
        inboxes = mailreef.get_inboxes()
        inboxes.sort(key=lambda x: x['id'])
        start, end = profile_config.get("inbox_indices", (0, 10))
        campaign_inboxes = inboxes[start:end]
        global FORWARD_FROM_INBOX
        FORWARD_FROM_INBOX = campaign_inboxes[0]['id'] if campaign_inboxes else inboxes[0]['id']
        print(f"📤 Forwarding from: {FORWARD_FROM_INBOX}")
    except Exception as e:
        print(f"⚠️ Could not get inboxes: {e}")
        FORWARD_FROM_INBOX = None
    
    # Load lead emails from the input sheet
    print("\n📋 Loading lead database from input sheet...")
    lead_emails = set()
    lead_domains = set()
    try:
        records = sheets.input_sheet.sheet1.get_all_records()
        for r in records:
            email = str(r.get('email', '')).lower().strip()
            if email:
                lead_emails.add(email)
                if '@' in email:
                    domain = email.split('@')[-1]
                    if domain not in GENERIC_DOMAINS:
                        lead_domains.add(domain)
        print(f"   ✅ {len(lead_emails)} leads, {len(lead_domains)} domains")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Load existing replies to avoid duplicates
    print("\n📋 Loading existing replies from sheet...")
    existing_reply_keys = set()
    try:
        reply_records = sheets.replies_sheet.sheet1.get_all_records()
        for r in reply_records:
            key = f"{r.get('From Email', '').lower()}|{r.get('Subject', '')}"
            existing_reply_keys.add(key)
        print(f"   ✅ {len(existing_reply_keys)} existing replies found")
    except Exception as e:
        print(f"   ⚠️ {e}")
    
    # Scan ALL inbound messages (past 7 days)
    since_dt = datetime.now() - timedelta(days=7)
    print(f"\n🔍 Scanning inbound mail since {since_dt.strftime('%Y-%m-%d')}...")
    
    real_replies = []
    total_scanned = 0
    warmup_count = 0
    
    for page in range(1, 10):  # Up to 1000 messages
        try:
            result = mailreef.get_global_inbound(page=page, display=100)
            batch = result.get("data", [])
            if not batch:
                break
            
            for msg in batch:
                total_scanned += 1
                from_email = str(msg.get("from_email", "")).lower().strip()
                subject = msg.get("subject_line", "")
                
                ts = msg.get("ts")
                if not ts:
                    continue
                msg_dt = datetime.fromtimestamp(ts)
                if msg_dt <= since_dt:
                    continue
                
                # Skip warmup
                subj_lower = subject.lower() if subject else ""
                is_warmup = any(p in subj_lower for p in WARMUP_PATTERNS)
                if is_warmup:
                    warmup_count += 1
                    continue
                
                # Lead-first check
                is_lead = from_email in lead_emails
                if not is_lead and '@' in from_email:
                    sender_domain = from_email.split('@')[-1]
                    if sender_domain in lead_domains:
                        is_lead = True
                
                if not is_lead:
                    # Check subject fragments for non-leads
                    reply_subject = subj_lower.replace('re:', '').replace('fwd:', '').strip()
                    known_fragments = [
                        "quick question", "supporting families", "boosting enrollment",
                        "academic outcomes", "differentiation", "merit scholarship",
                        "college readiness", "student-athletes", "test prep",
                        "enhancing value", "families and college prep"
                    ]
                    if not any(frag in reply_subject for frag in known_fragments):
                        continue
                
                # Get body
                body_text = msg.get("body_text")
                if not body_text and msg.get("body_html"):
                    body_text = re.sub('<[^<]+?>', '', msg.get("body_html"))
                body = body_text if body_text else msg.get("snippet_preview", "")
                
                # Check for duplicate
                dedup_key = f"{from_email}|{subject}"
                if dedup_key in existing_reply_keys:
                    continue
                existing_reply_keys.add(dedup_key)
                
                to_email = msg.get("to")[0] if msg.get("to") else "unknown"
                
                real_replies.append({
                    "from_email": from_email,
                    "subject": subject,
                    "body": body,
                    "date": msg_dt,
                    "inbox_email": to_email,
                    "is_lead": is_lead,
                    "thread_id": msg.get("thread_id", msg.get("conversation_id", ""))
                })
                
        except Exception as e:
            print(f"   ⚠️ Page {page} error: {e}")
            break
    
    print(f"\n📊 Scan Results:")
    print(f"   Total scanned: {total_scanned}")
    print(f"   Warmup filtered: {warmup_count}")
    print(f"   Real school replies found: {len(real_replies)}")
    
    if not real_replies:
        print("\n✅ No new replies found. Sheet is up to date.")
        return
    
    # Sort by date (newest first)
    real_replies.sort(key=lambda x: x["date"], reverse=True)
    
    # Analyze sentiment for each reply
    print(f"\n🧠 Analyzing sentiment for {len(real_replies)} replies...")
    for reply in real_replies:
        try:
            prompt = f"""Analyze the sentiment of this email reply from a school administrator.
Status options: 'positive' (interested, wants meeting, asks for info), 'negative' (not interested, unsubscribe, stop), 'neutral' (acknowledged, away, auto-reply).

REPLY:
{reply['body']}

Return ONLY one word: positive, negative, or neutral."""
            
            response = generator.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10
            )
            sentiment = response.choices[0].message.content.strip().lower()
        except Exception as e:
            sentiment = "neutral"
        
        reply["sentiment"] = sentiment
        
        # Actionable = positive or neutral (not a hard "no")
        reply["actionable"] = sentiment in ["positive", "neutral"]
        
        action_label = "✅ ACTIONABLE" if reply["actionable"] else "❌ NOT ACTIONABLE"
        print(f"   {action_label} | {reply['from_email']} | {sentiment} | {reply['subject'][:50]}")
    
    # Write to sheet (newest first, with color coding)
    print(f"\n📝 Writing {len(real_replies)} replies to sheet...")
    worksheet = sheets.replies_sheet.sheet1
    
    # Get current row count (to know where new rows start)
    current_rows = len(worksheet.get_all_values())
    
    new_rows = []
    for reply in real_replies:
        row = [
            reply["date"].isoformat(),
            reply["from_email"],
            "",  # from_name (not available from API)
            "",  # school_name (will be enriched by log_reply if called directly)
            "",  # role
            reply["subject"],
            reply["body"][:500],  # truncate long bodies
            reply["sentiment"],
            reply["inbox_email"],
            "",  # original_subject
            reply.get("thread_id", ""),
            "ACTIONABLE" if reply["actionable"] else "NOT ACTIONABLE",
            f"Lead match: {reply['is_lead']}"
        ]
        new_rows.append(row)
    
    # Insert rows at the TOP (row 2, right after header) so newest is first
    try:
        worksheet.insert_rows(new_rows, row=2)
        print(f"   ✅ Inserted {len(new_rows)} rows at the top of the sheet")
    except Exception as e:
        print(f"   ⚠️ Insert failed, falling back to append: {e}")
        for row in new_rows:
            worksheet.append_row(row)
    
    # Apply color coding
    print("\n🎨 Applying color coding (green=actionable, grey=not)...")
    try:
        import gspread
        from gspread_formatting import CellFormat, Color, format_cell_range
        
        green = CellFormat(backgroundColor=Color(0.85, 0.95, 0.85))  # Light green
        grey = CellFormat(backgroundColor=Color(0.9, 0.9, 0.9))      # Light grey
        
        for i, reply in enumerate(real_replies):
            row_num = i + 2  # 1-indexed, skip header
            fmt = green if reply["actionable"] else grey
            format_cell_range(worksheet, f"A{row_num}:M{row_num}", fmt)
        
        print(f"   ✅ Color coding applied to {len(real_replies)} rows")
    except ImportError:
        print("   ⚠️ gspread_formatting not available — trying batch API directly...")
        try:
            sheet_id = worksheet.id
            requests = []
            for i, reply in enumerate(real_replies):
                row_idx = i + 1  # 0-indexed, skip header
                if reply["actionable"]:
                    bg = {"red": 0.85, "green": 0.95, "blue": 0.85}
                else:
                    bg = {"red": 0.9, "green": 0.9, "blue": 0.9}
                
                requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": row_idx,
                            "endRowIndex": row_idx + 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 13
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": bg
                            }
                        },
                        "fields": "userEnteredFormat.backgroundColor"
                    }
                })
            
            if requests:
                sheets.replies_sheet.batch_update({"requests": requests})
                print(f"   ✅ Color coding applied via batch API")
        except Exception as e:
            print(f"   ⚠️ Color coding failed: {e}")
    except Exception as e:
        print(f"   ⚠️ Color coding error: {e}")
    
    # Forward all real replies
    print(f"\n📤 Forwarding {len(real_replies)} replies to {', '.join(FORWARD_TO)}...")
    if FORWARD_FROM_INBOX:
        for reply in real_replies:
            action_label = "🟢 ACTIONABLE" if reply["actionable"] else "🔴 NOT ACTIONABLE"
            forward_subject = f"[IVY BOUND REPLY - {action_label}] {reply['subject']}"
            forward_body = f"""<div style="font-family: Arial, sans-serif; padding: 20px;">
<h2 style="color: {'#2e7d32' if reply['actionable'] else '#666'};">{action_label}</h2>
<hr>
<p><strong>From:</strong> {reply['from_email']}</p>
<p><strong>To:</strong> {reply['inbox_email']}</p>
<p><strong>Date:</strong> {reply['date'].strftime('%B %d, %Y at %I:%M %p')}</p>
<p><strong>Subject:</strong> {reply['subject']}</p>
<p><strong>Sentiment:</strong> {reply['sentiment'].upper()}</p>
<p><strong>Lead Match:</strong> {'✅ Yes' if reply['is_lead'] else '❌ No'}</p>
<hr>
<h3>Reply Content:</h3>
<blockquote style="border-left: 3px solid #ccc; padding-left: 15px; color: #333;">
{reply['body']}
</blockquote>
</div>"""
            
            for forward_to in FORWARD_TO:
                try:
                    mailreef.send_email(
                        FORWARD_FROM_INBOX,
                        forward_to,
                        forward_subject,
                        forward_body
                    )
                    print(f"   ✅ Forwarded to {forward_to}: {reply['from_email']}")
                    time.sleep(1)  # Rate limit
                except Exception as e:
                    print(f"   ❌ Forward to {forward_to} failed: {e}")
    else:
        print("   ❌ No forwarding inbox available")
    
    # Summary
    actionable = [r for r in real_replies if r["actionable"]]
    not_actionable = [r for r in real_replies if not r["actionable"]]
    
    print(f"\n{'=' * 60}")
    print(f"📊 AUDIT COMPLETE")
    print(f"{'=' * 60}")
    print(f"   Total real replies: {len(real_replies)}")
    print(f"   🟢 Actionable: {len(actionable)}")
    print(f"   🔴 Not actionable: {len(not_actionable)}")
    print(f"   📝 Written to: {profile_config['replies_sheet']}")
    print(f"   📤 Forwarded to: {', '.join(FORWARD_TO)}")
    
    # Telegram summary
    try:
        summary = f"📬 *Reply Audit Complete*\n\n"
        summary += f"Found {len(real_replies)} replies\n"
        summary += f"🟢 Actionable: {len(actionable)}\n"
        summary += f"🔴 Not actionable: {len(not_actionable)}\n\n"
        for r in real_replies[:10]:  # Top 10
            icon = "🟢" if r["actionable"] else "🔴"
            summary += f"{icon} {r['from_email']}: {r['sentiment']}\n"
        telegram.send_message(summary)
    except:
        pass


if __name__ == "__main__":
    main()
