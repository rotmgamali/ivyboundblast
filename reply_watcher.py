import os
import json
import logging
import time
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Add project root path
import sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "mailreef_automation"))
sys.path.insert(0, BASE_DIR)

from mailreef_automation.mailreef_client import MailreefClient
from mailreef_automation.contact_manager import ContactManager
from mailreef_automation.telegram_alert import TelegramNotifier
from sheets_integration import GoogleSheetsClient
from generators.email_generator import EmailGenerator
import lock_util

# Configuration
MAILREEF_API_KEY = os.getenv("MAILREEF_API_KEY")
if not MAILREEF_API_KEY:
    load_dotenv()
    MAILREEF_API_KEY = os.getenv("MAILREEF_API_KEY")

STATE_FILE = "mailreef_automation/logs/reply_watcher_state.json"
CHECK_INTERVAL_MINUTES = 5

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("REPLY_WATCHER")


class ReplyWatcher:
    def __init__(self):
        # Ensure only one instance runs
        lock_util.ensure_singleton('watcher')
        
        self.state_file = STATE_FILE
        self.mailreef = MailreefClient(api_key=MAILREEF_API_KEY)
        self.contact_manager = ContactManager(database_path=os.path.join(BASE_DIR, "mailreef_automation/campaign.db"))
        self.sheets_client = GoogleSheetsClient()
        self.telegram = TelegramNotifier()
        self.generator = EmailGenerator() # Used for sentiment analysis
        
    def load_state(self) -> dict:
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {"last_check": (datetime.now() - timedelta(hours=24)).isoformat()}

    def save_state(self, state: dict):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(state, f)

    def get_inbox_replies(self, since: str) -> List[Dict]:
        replies = []
        try:
            # 1. Fetch all inboxes using established logic
            inboxes = self.mailreef.get_inboxes()
            
            for inbox in inboxes:
                inbox_id = inbox.get("id")
                # Get messages/received for this inbox
                # Mailreef API: /mailboxes/{id}/messages
                response = self.mailreef.session.get(
                    f"{self.mailreef.base_url}/mailboxes/{inbox_id}/messages", 
                    params={"since": since, "type": "received"}
                )
                
                if response.ok:
                    inbox_msgs = response.json()
                    # Handle both list and dict response
                    batch = inbox_msgs.get("data", inbox_msgs) if isinstance(inbox_msgs, dict) else inbox_msgs
                    if isinstance(batch, dict): batch = batch.get("messages", [])
                    
                    if batch:
                        for msg in batch:
                            msg["inbox_email"] = inbox.get("email")
                            msg["inbox_id"] = inbox_id
                            replies.append(msg)
                        
        except Exception as e:
            logger.error(f"Mailreef API Error: {e}")
        
        return replies

    def analyze_sentiment(self, text: str) -> str:
        """Use GPT-4o-mini to check for high interest/positive sentiment."""
        prompt = f"""Analyze the sentiment of this email reply from a school administrator.
Status options: 'positive' (interested, wants meeting, asks for info), 'negative' (not interested, stop), 'neutral' (acknowledged, away).

REPLY:
{text}

Return ONLY one word: positive, negative, or neutral."""
        
        try:
            response = self.generator.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10
            )
            return response.choices[0].message.content.strip().lower()
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return "neutral"

    def process_replies(self):
        state = self.load_state()
        last_check = state.get("last_check")
        
        logger.info(f"Checking for replies since {last_check}")
        replies = self.get_inbox_replies(last_check)
        logger.info(f"Found {len(replies)} new replies")
        
        for reply in replies:
            from_email = reply.get('from_email')
            body = reply.get('body', '')
            subject = reply.get('subject', '')
            
            # 1. Update SQLite (Auto-cancel future follow-ups)
            self.contact_manager.update_contact_status(from_email, 'replied')
            
            # 2. Sentiment Analysis
            sentiment = self.analyze_sentiment(body)
            logger.info(f"Sentiment for {from_email}: {sentiment}")
            
            # 3. Log to Google Sheets
            reply_data = {
                'received_at': reply.get('date', datetime.now().isoformat()),
                'from_email': from_email,
                'subject': subject,
                'snippet': body[:200],
                'sentiment': sentiment,
                'original_sender': reply.get('inbox_email'),
                'thread_id': reply.get('thread_id', reply.get('conversation_id'))
            }
            try:
                self.sheets_client.log_reply(reply_data)
            except Exception as e:
                logger.error(f"Failed to log to sheets: {e}")
            
            # 4. Telegram Alert for Positive Sentiment
            if sentiment == 'positive':
                alert_text = f"🔥 *HOT LEAD REPLY*\n\n*From:* {from_email}\n*Subject:* {subject}\n\n*Snippet:*\n`{body[:300]}...`"
                self.telegram.send_message(alert_text)
                logger.info(f"🚀 Telegram alert sent for {from_email}")

        # Update state
        state["last_check"] = datetime.now().isoformat()
        state["last_run"] = datetime.now().isoformat()
        self.save_state(state)
        logger.info("✅ Reply check cycle completed.")

    def run_daemon(self):
        logger.info(f"Starting Reply Watcher daemon (every {CHECK_INTERVAL_MINUTES}m)")
        while True:
            try:
                self.process_replies()
            except Exception as e:
                logger.error(f"Error in daemon: {e}")
            time.sleep(CHECK_INTERVAL_MINUTES * 60)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--daemon", action="store_true")
    args = parser.parse_args()
    
    watcher = ReplyWatcher()
    try:
        if args.daemon:
            watcher.run_daemon()
        else:
            watcher.process_replies()
    finally:
        lock_util.release_lock('watcher')

if __name__ == "__main__":
    main()
