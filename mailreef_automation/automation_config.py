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
INBOXES_PER_DAY_BUSINESS = 95  # Maximize: All inboxes active
INBOXES_PER_DAY_WEEKEND = 95   # All inboxes active on weekends
INBOX_PAUSED_IDS = []          # Dynamic pause list for health monitoring

EMAILS_PER_INBOX_DAY_BUSINESS = 5   # Static fallback. The live cap comes from get_current_ramp_caps().
EMAILS_PER_INBOX_DAY_WEEKEND = 3    # Static fallback. The live cap comes from get_current_ramp_caps().

# ==================== WEEKLY RAMP (auto-escalating) ====================
# Set when the senders went live on Railway. Override via the
# CAMPAIGN_START_DATE env var to reset / pause the ramp.
# Reset 2026-05-05 to slow-warm cold domains. After 4 days at 5/inbox/day
# we hit 0 replies on 2,794 sends — strong signal of spam-folder placement.
# Slow ramp lets reputation rebuild via Smartlead warmup before pushing
# cold-outreach volume back up.
CAMPAIGN_START_DATE = os.environ.get("CAMPAIGN_START_DATE", "2026-05-05")
# 2026-05-11: Bumped to max-safe rate. User explicitly asking for max
# volume. Competitionhand tested 3/3 Inbox at Gmail so domains can take
# 5-10/inbox/day right now. Ramp tops out at 10 — anything higher risks
# tripping spam filters even on warm domains.
WEEKLY_RAMP_BUSINESS = [5, 8, 10, 10]
WEEKLY_RAMP_WEEKEND = [3, 5, 7, 7]


def get_current_ramp_caps(today=None):
    """Return today's per-inbox caps based on weeks since CAMPAIGN_START_DATE.

    Returns a dict with business/weekend per-inbox targets, the max daily cap
    (= business target), and the 1-indexed week number for logging.
    """
    from datetime import date
    if today is None:
        today = date.today()
    try:
        start = date.fromisoformat(CAMPAIGN_START_DATE)
    except Exception:
        start = today
    days = max(0, (today - start).days)
    week_idx = min(len(WEEKLY_RAMP_BUSINESS) - 1, days // 7)
    return {
        "business": WEEKLY_RAMP_BUSINESS[week_idx],
        "weekend": WEEKLY_RAMP_WEEKEND[week_idx],
        "max_per_inbox": WEEKLY_RAMP_BUSINESS[week_idx],
        "week": week_idx + 1,
    }

# ==================== TELEGRAM ALERTS ====================
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""

# ==================== SENDING WINDOWS (24-hour format, EST) ====================
# WEEK 1 conservative ramp: 5 emails/inbox/day spread across 5 windows (1 each)
BUSINESS_DAY_WINDOWS = [
    {"start": 9, "end": 10, "emails_per_inbox": 1},
    {"start": 11, "end": 12, "emails_per_inbox": 1},
    {"start": 13, "end": 14, "emails_per_inbox": 1},
    {"start": 14, "end": 15, "emails_per_inbox": 1},
    {"start": 15, "end": 16, "emails_per_inbox": 1},  # Total: 5
]

# Weekend: 3 emails/inbox/day across 3 windows
WEEKEND_DAY_WINDOWS = [
    {"start": 10, "end": 11, "emails_per_inbox": 1},
    {"start": 12, "end": 13, "emails_per_inbox": 1},
    {"start": 14, "end": 15, "emails_per_inbox": 1},  # Total: 3
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
SUPPRESSION_SHEET_NAME = "Master Suppression List"
ACTIVE_REPLIES_WORKSHEET = "Sheet 1" # Monthly tracking

CAMPAIGN_CONFIG = {
    "sequence_length": 2,  # 2-email sequence: Email 1 + follow-up Email 2
    "days_between_sequence": 4,  # Day 0, Day 4
    "max_retries": 3,
    "retry_delay_hours": 24,
    "stop_on_hard_bounce": True,
    "pause_on_complaint": True,
}

# ==================== CAN-SPAM COMPLIANCE ====================
# CAN-SPAM compliance footer. Real values required — leaked placeholders
# are spam-filter triggers AND look unprofessional to recipients.
# YOU MUST set PHYSICAL_ADDRESS and UNSUBSCRIBE_MAILTO via Railway env vars
# to your real business address and unsubscribe mailbox before re-launching.
# Until then, the footer is suppressed entirely (see scheduler.py emit logic
# which only renders the footer when both values are non-empty).
PHYSICAL_ADDRESS = os.environ.get("PHYSICAL_ADDRESS", "")
UNSUBSCRIBE_MAILTO = os.environ.get("UNSUBSCRIBE_MAILTO", "")
MAX_DAILY_SENDS_PER_INBOX = 5  # WEEK 1 cap. Bump to 10 (week 2), 15 (week 3), 20 (week 4+)

# ==================== DELIVERABILITY THRESHOLDS ====================
COMPLAINT_RATE_THRESHOLD = 0.003  # 0.3% — industry standard (was 1%)
BOUNCE_RATE_THRESHOLD = 0.02      # 2% — tighter than previous 5%

# ==================== SENDER IDENTITIES ====================
SENDER_IDENTITIES = {
    "mark": {"name": "Mark Greenstein", "title": "Ivybound Education Partners"},
    "genelle": {"name": "Genelle Carter", "title": "Ivybound Education Partners"},
    "andrew": {"name": "Andrew Rollins", "title": "Ivybound Education Partners"},
    "outreach": {"name": "Andrew Rollins", "title": "Ivybound Education Partners"},
    "default": {"name": "Andrew Rollins", "title": "Ivybound Education Partners"},
}

# Per-campaign sender identity overrides — used when a campaign needs
# different signatures (e.g. Bahamas retreat sells from a different brand)
BAHAMAS_SENDER_IDENTITIES = {
    "andrew": {"name": "Andrew", "title": "SerenitySpaces Bahamas"},
    "mark": {"name": "Mark", "title": "SerenitySpaces Bahamas"},
    "genelle": {"name": "Genelle", "title": "SerenitySpaces Bahamas"},
    "outreach": {"name": "Andrew", "title": "SerenitySpaces Bahamas"},
    "alex": {"name": "Alex", "title": "SerenitySpaces Bahamas"},
    "default": {"name": "Andrew", "title": "SerenitySpaces Bahamas"},
}

# ==================== DAY MAPPING ====================
# 0 = Monday, 6 = Sunday
BUSINESS_DAY_INDICES = [0, 1, 2, 3, 4]  # Mon-Fri
WEEKEND_DAY_INDICES = [5, 6]  # Sat-Sun

# ==================== CAMPAIGN PROFILES ====================
# Inbox Indices: Slicing logic [start, end)
CAMPAIGN_PROFILES = {
    "IVYBOUND": {
        "input_sheet": "Ivy Bound - Campaign Leads",
        "replies_sheet": "Ivy Bound - Reply Tracking",
        "replies_sheet_id": "1jeLkdufaMub4rylaPnoTQZwDiLpHmut5hcQQStl8UxI",
        "send_window_group": "default",
        "inbox_indices": (0, 88),  # All truckice inboxes
        "log_file": "ivybound.log",
        "template_dir": "templates",
        "campaign_type": "school",
        "subject_patterns": ["Quick question about", "Quick question for"],
        "server_filter": "truckice"  # Migrated from dead errorskin
    },
    "IVYBOUND_SUMMER": {
        "input_sheet": "Ivy Bound - Campaign Leads",
        "replies_sheet": "Ivy Bound - Reply Tracking",
        "replies_sheet_id": "1jeLkdufaMub4rylaPnoTQZwDiLpHmut5hcQQStl8UxI",
        "send_window_group": "default",
        "log_file": "ivybound_summer.log",
        "templates_dir": "templates/school_summer",  # Summer-angled templates
        # IV uses truckice (burned) — keep volume LOW to avoid amplifying
        # reputation damage. Override the global ramp at a static 2/day
        # regardless of week. 88 inboxes × 2 = 176/day, ~33% delivered
        # given burn = ~58 effectively-inboxed per day. Acceptable risk
        # to keep some IV stage-1 outreach alive on the asset.
        "daily_cap_override": 2,
        "campaign_type": "school",
        # Subject patterns — dropped "Quick question about" after 2026-05-05
        # deliverability test: that subject is a known top-tier spam trigger
        # at Gmail/Outlook ML and likely contributed to truckice domain
        # reputation damage from the March campaign.
        "subject_patterns": [
            "Summer enrichment for {{ school_name }}",
            "{{ school_name }} families and college prep",
            "Summer SAT prep at private-school pricing",
            "A no-cost resource for your families this summer",
        ],
        # 2026-05-11: User wants both servers utilized at max volume.
        # BAH took the clean competitionhand cluster (84 inboxes), IV
        # goes back to truckice (88 inboxes) at low rate (2/day cap)
        # to avoid amplifying the burn while still extracting some
        # value from the asset. 88 × 2 = 176/day stage-1 IV sends.
        "server_filter": "truckice",
        # Stage-2 follow-ups DISABLED 2026-05-05. Even on fresh
        # competitionhand domains, re-engaging the March cohort (who
        # already didn't open the IV email then) is poor use of the new
        # reputation budget. Stage-1 fresh leads only.
        "disable_followups": True,
        "archetypes": {
            "head_of_school": ["head of school", "headmaster", "headmistress", "president", "executive director", "superintendent"],
            "principal": ["principal", "assistant principal", "vice principal"],
            "academic_dean": ["dean", "academic", "curriculum", "instruction"],
            "college_counseling": ["counselor", "college", "guidance", "advisor"],
            "business_manager": ["business", "finance", "cfo", "bursar", "operations"],
        },
    },
    "BAHAMAS_RETREAT": {
        # Workaround: store Bahamas leads in a TAB inside the existing Ivy Bound
        # spreadsheet because the service account's Drive quota is full.
        "input_sheet": "Ivy Bound - Campaign Leads",
        "input_worksheet": "Bahamas Retreat - Leads",
        "replies_sheet": "Ivy Bound - Reply Tracking",
        "send_window_group": "default",
        "log_file": "bahamas_retreat.log",
        "templates_dir": "templates/bahamas",
        "campaign_type": "b2b",
        "subject_patterns": [
            "private property",
            "private villa",
            "executive offsite",
            "team retreat",
            "{{ company_name }}",
        ],
        # 2026-05-10: All 84 competitionhand inboxes assigned to Bahamas
        # (IVYBOUND_SUMMER paused per user priority). domain_whitelist
        # removed so server_filter alone admits the full set.
        "server_filter": "competitionhand",
        "sender_identities_override": "BAHAMAS_SENDER_IDENTITIES",
        "system_prompt_template": (
            "You are {sender_name} from SerenitySpaces Bahamas, a private 4-villa luxury retreat property "
            "in Freeport, Grand Bahama. You are writing a peer-to-peer email to an executive who might "
            "host a corporate retreat, executive offsite, or team event at the property. The villas sleep "
            "up to 22 across the full property, $150-650/night, 35 minutes by air from Fort Lauderdale, "
            "5-minute walk to Coral Beach, USD pricing, no visa for US citizens.\n\n"
            "VOICE: Confident, peer-to-peer, NEVER corporate. Short sentences. Tight paragraphs.\n"
            "BANNED PHRASES: 'I noticed', 'I'd love to', 'reaching out', 'touching base', 'synergy', 'leverage'.\n"
            "RULES: 1) NO greeting, 2) NO sign-off, 3) Output ONLY Subject + Body, 4) NO placeholder brackets.\n"
            "If research is empty, write a clean professional pitch without faking specifics."
        ),
        "archetypes": {
            "ceo_founder": ["ceo", "founder", "owner", "president", "managing partner", "chief executive"],
            "coo_cfo": ["coo", "cfo", "cmo", "cto", "evp", "executive vice president", "chief"],
            "director": ["vp", "vice president", "director", "head of"],
        },
    },
    "STRATEGY_B": {
        "input_sheet": "Web4Guru - Campaign Leads",
        "replies_sheet": "Web4Guru - Reply Tracking",
        "send_window_group": "default",
        "campaign_type": "b2b",
        "inbox_indices": (0, 67), # Uses the 67 birdsgeese inboxes
        "log_file": "web4guru.log",
        "templates_dir": "templates_strategy_b",
        "archetypes": {
            "executive": ["ceo", "founder", "owner", "president", "partner", "vp", "executive"],
            "marketing": ["marketing", "growth", "branding", "digital"],
            "sales": ["sales", "revenue", "business development", "partnerships"],
            "operations": ["operations", "coo", "manager", "principal"]
        },
        "subject_patterns": ["Question for", "AI tools", "growth strategies"],
        "server_filter": "birdsgeese"
    },
    "WEB4GURU_ACCOUNTANTS": {
        "input_sheet": "Web4Guru Accountants - Campaign Leads",
        "replies_sheet": "Web4Guru Accountants - Reply Tracking",
        "send_window_group": "default", # Same window as others
        "campaign_type": "b2b",
        "inbox_indices": (67, 162), # Uses the 95 errorskin inboxes (verified 67-161)
        "log_file": "web4guru_accountants.log",
        "templates_dir": "templates/web4guru/accountants", # Base dir for templates
        "reply_prompt": "prompts/web4guru_accountant_reply.txt",
        "reply_prompt": "prompts/web4guru_accountant_reply.txt",
        "auto_reply_template": "b2b/general/email_2.txt",
        "subject_patterns": ["Inquiry", "Question", "Growth /", "Accounting growth"],
        "server_filter": "errorskin"
    },
    "DEMONS_AND_DEITIES": {
        "input_sheet": "Demons & Deities - Campaign Leads",
        "replies_sheet": "Demons & Deities - Reply Tracking",
        "send_window_group": "default",
        "campaign_type": "crypto",
        "inbox_indices": (0, 95), # Uses all 95 truckice inboxes
        "log_file": "demons_deities.log",
        "templates_dir": "templates/crypto",
        "archetypes": {
            "influencer": ["influencer", "content creator", "youtuber", "streamer", "reviewer", "creator", "host", "podcaster"],
            "investor": ["vc", "venture", "capital", "fund", "investor", "investment", "partner", "analyst"],
            "promoter": ["marketing", "promotion", "pr", "media", "advertising", "agency", "growth", "shill", "caller", "alpha"],
            "general": ["general", "project", "protocol", "guild", "dao", "community"]
        },
        "subject_patterns": ["TFT meets blockchain", "NFT auto-battler", "Polygon game"],
        "server_filter": "truckice"
    }
}

# ==================== INBOX ROTATION ====================
# Rotation is now handled dynamically in scheduler.py

