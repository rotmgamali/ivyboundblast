"""
Configuration for 50,000/month Mailreef cold email automation
Target: School administrators (public + private schools)
"""
import os
from dotenv import load_dotenv

# Add project root to path for .env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# ==================== TARGET METRICS ====================
MONTHLY_EMAIL_TARGET = 50000
BUSINESS_DAYS_PER_MONTH = 22
WEEKEND_DAYS_PER_MONTH = 8

# ==================== INBOX CONFIGURATION ====================
TOTAL_INBOXES = 95
INBOXES_PER_DAY_BUSINESS = 93  # 2 inboxes paused for precision
INBOXES_PER_DAY_WEEKEND = 95   # All inboxes active on weekends
INBOX_PAUSED_IDS = []          # Dynamic pause list for health monitoring

EMAILS_PER_INBOX_DAY_BUSINESS = 21
EMAILS_PER_INBOX_DAY_BUSINESS = 21
EMAILS_PER_INBOX_DAY_WEEKEND = 9

# ==================== TELEGRAM ALERTS ====================
TELEGRAM_BOT_TOKEN = "7224632370:AAFgWL94FbffWBO6COKnYyhrMKymFJQV0po"
TELEGRAM_CHAT_ID = "7059103286" # Auto-discovered (Andrew Rollins)

# ==================== SENDING WINDOWS (24-hour format, EST) ====================
# Business days: 6:00 - 19:30 (avoid 11:00-14:00 busy hours)
BUSINESS_DAY_WINDOWS = [
    {"start": 6, "end": 7, "emails_per_inbox": 2},
    {"start": 7, "end": 8, "emails_per_inbox": 2},
    {"start": 8, "end": 9, "emails_per_inbox": 3},
    {"start": 9, "end": 10, "emails_per_inbox": 3},
    {"start": 10, "end": 11, "emails_per_inbox": 3},
    {"start": 12, "end": 13, "emails_per_inbox": 3}, # Added for immediate live launch
    {"start": 15, "end": 16, "emails_per_inbox": 2},
    {"start": 16, "end": 17, "emails_per_inbox": 2},
    {"start": 17, "end": 18, "emails_per_inbox": 2},
    {"start": 18, "end": 19, "emails_per_inbox": 2},
]

# Weekend days: 19:00 - 20:30
WEEKEND_DAY_WINDOWS = [
    {"start": 19, "end": 20, "emails_per_inbox": 5},
    {"start": 20, "end": 21, "emails_per_inbox": 4},
]

# Quiet hours: No sending
QUIET_HOURS = {"start": 21, "end": 5}

# ==================== MAILREEF API CONFIG ====================
MAILREEF_API_BASE = os.environ.get("MAILREEF_API_BASE") or "https://api.mailreef.com"
MAILREEF_API_KEY = os.environ.get("MAILREEF_API_KEY")

# Check if key is missing and try to reload if local
if not MAILREEF_API_KEY:
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
    MAILREEF_API_KEY = os.environ.get("MAILREEF_API_KEY")

# ==================== CAMPAIGN SETTINGS ====================
CAMPAIGN_CONFIG = {
    "sequence_length": 2,  # 2-email sequence
    "days_between_sequence": 4,  # Day 0, Day 4
    "max_retries": 3,
    "retry_delay_hours": 24,
    "stop_on_hard_bounce": True,
    "pause_on_complaint": True,
}

# ==================== DAY MAPPING ====================
# 0 = Monday, 6 = Sunday
BUSINESS_DAY_INDICES = [0, 1, 2, 3, 4]  # Mon-Fri
WEEKEND_DAY_INDICES = [5, 6]  # Sat-Sun

# ==================== INBOX ROTATION ====================
# Rotation is now handled dynamically in scheduler.py

