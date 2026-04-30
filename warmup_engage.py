"""
Warming Engagement Daemon for Mailreef Inboxes

Continuously monitors inbound warming emails and sends natural-looking replies
to signal engagement to Mailreef's warming network. This is the missing piece
that gets your inboxes warmed up properly — Mailreef sends warming emails IN,
this script makes sure they get replies BACK.

Modes:
    Daemon (continuous):  python3 warmup_engage.py --daemon
    Single run:           python3 warmup_engage.py
    Dry run preview:      python3 warmup_engage.py --dry-run

Options:
    --interval 600    Daemon poll interval in seconds (default: 600 = 10 min)
    --limit 100       Max replies per cycle (default: 100)
    --min-delay 3     Min seconds between replies (default: 3)
    --max-delay 12    Max seconds between replies (default: 12)
"""
import os
import sys
import json
import random
import time
import argparse
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import requests

API_KEY = os.environ["MAILREEF_API_KEY"]
BASE_URL = "https://api.mailreef.com"
STATE_FILE = "warmup_engage_state.json"
MAX_STATE_IDS = 20000  # Cap state file size

session = requests.Session()
session.auth = (API_KEY, "")
session.headers.update({"Content-Type": "application/json"})

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("warmup_engage.log"),
    ],
)
logger = logging.getLogger("warmup_engage")

# ============================================================================
# REPLY SNIPPETS — varied, natural, business-context-aware
# ============================================================================
REPLY_SNIPPETS = [
    "Thanks for the update! I'll take a look at this and follow up.",
    "Appreciate you sending this over. Let me review and get back to you.",
    "Got it, thanks! I'll loop back on this shortly.",
    "Thanks for sharing — this is really helpful. Let's discuss further.",
    "Great info, appreciate the heads up. I'll check my schedule.",
    "Thanks! I've noted this down. Will circle back soon.",
    "Really appreciate the follow-up on this. Let me review the details.",
    "This is great, thanks for putting it together. I'll take a closer look.",
    "Thanks for the reminder! I'll get on this today.",
    "Good to know — thanks for keeping me in the loop on this.",
    "Appreciate the update. I'll coordinate on my end and let you know.",
    "Thanks! This aligns with what we discussed. I'll follow up shortly.",
    "Got it. Let me check a few things on my end and I'll respond properly.",
    "Thanks for flagging this. I'll review and share my thoughts.",
    "Sounds good! I'll take a look and get back to you by end of day.",
    "Thanks for the note. Let me think on this and get back to you.",
    "Good catch — I'll factor this into my planning.",
    "Appreciate it. I'll add this to my list and follow up.",
    "Thanks, this is useful. Will get back to you when I have a moment.",
    "Got it, thanks for sending. I'll review and respond soon.",
    "Thanks for keeping me posted. I'll follow up after I've reviewed.",
    "Helpful, thank you. I'll take this into consideration.",
    "Thanks for taking the time to send this over.",
    "Appreciate the info. Will circle back once I've had a chance to look.",
    "Thanks! Will get on this and reply with thoughts soon.",
]

# ============================================================================
# WARMING DETECTION — multi-signal classification
# ============================================================================
WARMING_BODY_TAGS = [
    "other-", "stock-globe", "blank-order", "arrow-swept", "lower-speed",
    "build-catch", "occur-light", "thumb-grown", "offer-basic", "ought-stone",
    "slept-graph", "allow-there", "clean-split", "thumb-prove", "store-block",
]

WARMING_SUBJECTS = [
    "wellness workshop", "expense report", "vendor negotiation",
    "project update", "project timeline", "webinar announcement",
    "feedback on", "volunteer", "satisfaction survey",
    "book recommendation", "engineering challenge", "financial report",
    "corporate social responsibility", "client feedback", "deployment",
    "management tools", "training session", "team building",
    "internal job posting", "travel plans", "office space",
    "marketing strategy", "event invitation", "policy update",
    "quarterly", "compliance", "performance review", "hr update",
    "tool integration", "productivity", "remote work", "new compliance",
    "research project", "marketing campaign", "health and wellness",
    "yoga class", "book club", "improvements in", "incident #",
    "annual sales", "industry conference", "presentation skills",
]

# Warming network domains we've observed (from earlier data analysis)
WARMING_DOMAINS = [
    "savoir", "influutap", "influumcn", "influuagency", "mcninfluu",
    "influutkmcn", "gcodepad", "toolai.club", "rapidfab", "fabunit",
    "fabcore", "robtronicmedia", "brandingsavoir", "mumbaisavoir",
    "marketingsavoir", "firmsavoir", "saassavoir", "developmentsavoir",
    "globalsavoir", "circleuphello", "breezezeal", "leverjs",
    "xenialverdant", "limedate", "flirtyfellow", "loversnestle",
    "franchise-growth", "trydashadpay", "leaderscohort", "robtronic",
    "high-bridge-academy", "samanage.com", "sd10ithelp", "gcodeai",
]

# ============================================================================
# STATE PERSISTENCE
# ============================================================================
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
                state["replied_ids"] = set(state.get("replied_ids", []))
                return state
        except Exception as e:
            logger.warning(f"Could not load state: {e}")
    return {"replied_ids": set(), "last_run": None, "total_sent": 0}


def save_state(state):
    state_to_save = dict(state)
    # Cap the replied IDs list size and convert to list
    replied_list = list(state["replied_ids"])
    if len(replied_list) > MAX_STATE_IDS:
        replied_list = replied_list[-MAX_STATE_IDS:]
    state_to_save["replied_ids"] = replied_list
    state_to_save["last_run"] = datetime.now().isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state_to_save, f, indent=2)


# ============================================================================
# LEAD PROTECTION — never reply to a real prospect's email
# ============================================================================
def get_dead_domains():
    """Fetch current dead/inactive inbox domains from Mailreef."""
    dead = set()
    try:
        for server in ["truckice", "competitionhand"]:
            page = 1
            while True:
                r = session.get(
                    f"{BASE_URL}/mailboxes",
                    params={"page": page, "display": 100, "server": server},
                    timeout=30,
                )
                if r.status_code != 200:
                    break
                batch = r.json().get("data", [])
                if not batch:
                    break
                for m in batch:
                    if not m.get("live") and "@" in (m.get("id") or ""):
                        dead.add(m["id"].split("@")[1])
                if len(batch) < 100:
                    break
                page += 1
    except Exception as e:
        logger.warning(f"Could not fetch dead inboxes: {e}")
    return dead


def get_live_mailboxes_by_domain():
    """Map each domain to its list of live mailbox email addresses."""
    domain_map = {}
    try:
        for server in ["truckice", "competitionhand"]:
            page = 1
            while True:
                r = session.get(
                    f"{BASE_URL}/mailboxes",
                    params={"page": page, "display": 100, "server": server},
                    timeout=30,
                )
                if r.status_code != 200:
                    break
                batch = r.json().get("data", [])
                if not batch:
                    break
                for m in batch:
                    mbox_id = m.get("id") or ""
                    if m.get("live") and "@" in mbox_id:
                        domain = mbox_id.split("@")[1]
                        domain_map.setdefault(domain, []).append(mbox_id)
                if len(batch) < 100:
                    break
                page += 1
    except Exception as e:
        logger.warning(f"Could not fetch live mailboxes: {e}")
    return domain_map


def is_warming_email(email_data):
    """Multi-signal warming detection. Be conservative — when in doubt, skip."""
    from_email = (email_data.get("from_email") or "").lower()
    subject = (email_data.get("subject_line") or "").lower()
    body = (email_data.get("body_text") or "").lower()[:1000]
    snippet = (email_data.get("snippet_preview") or "").lower()
    headers = email_data.get("headers", {}) or {}

    # SIGNAL 1: Body contains a warming network tag (strongest signal)
    if any(tag in body or tag in snippet for tag in WARMING_BODY_TAGS):
        return True

    # SIGNAL 2: From a known warming network domain
    if any(wd in from_email for wd in WARMING_DOMAINS):
        return True

    # SIGNAL 3: Sent via Amazon SES + matches a warming subject pattern
    msg_id = str(headers.get("Message_Id", ""))
    if "amazonses.com" in msg_id and any(ws in subject for ws in WARMING_SUBJECTS):
        return True

    return False


def is_real_lead_email(email_data):
    """Detect if this is a reply from a REAL prospect (school, business, etc.).
    If yes, NEVER reply to it — it would corrupt our reply tracking."""
    from_email = (email_data.get("from_email") or "").lower()
    subject = (email_data.get("subject_line") or "").lower()

    # Real lead indicators (.edu, .k12., .gov domains)
    if ".edu" in from_email or ".k12." in from_email or ".gov" in from_email:
        return True

    # Subject contains "Re: Quick question about" or "Re: Supporting families at"
    # These are our outbound subject patterns — replies to them are real leads
    real_reply_patterns = [
        "re: quick question about", "re: supporting families at",
        "re: question about", "re: curious about",
        "re: enhancing", "re: empowering",
    ]
    if any(p in subject for p in real_reply_patterns):
        return True

    return False


# ============================================================================
# CORE LOGIC
# ============================================================================
def fetch_recent_inbound(max_pages=5):
    """Fetch recent inbound emails (most recent first)."""
    all_emails = []
    for page in range(1, max_pages + 1):
        try:
            r = session.get(
                f"{BASE_URL}/mail/inbound",
                params={"page": page, "display": 100},
                timeout=30,
            )
            if r.status_code != 200:
                break
            data = r.json()
            emails = data.get("data", [])
            if not emails:
                break
            all_emails.extend(emails)
            if len(emails) < 100:
                break
        except Exception as e:
            logger.error(f"Fetch error on page {page}: {e}")
            break
    return all_emails


def reply_to_warming_email(email_data, dead_domains, live_mailboxes, dry_run=False):
    """Send a natural reply to a warming email. Returns (success, reason)."""
    msg_id = email_data.get("message_id")
    from_email = email_data.get("from_email")
    to_inbox = email_data.get("to", [None])
    if isinstance(to_inbox, list):
        to_inbox = to_inbox[0] if to_inbox else None

    if not all([msg_id, from_email, to_inbox]):
        return False, "missing fields"

    # Skip dead domains
    inbox_domain = to_inbox.split("@")[1] if "@" in to_inbox else ""
    if inbox_domain in dead_domains:
        return False, "dead domain"

    # If the recipient is a catch-all address (not a real mailbox on our account),
    # substitute a real live mailbox on the same domain for the reply
    domain_mailboxes = live_mailboxes.get(inbox_domain, [])
    if not domain_mailboxes:
        return False, f"no live mailboxes on {inbox_domain}"

    if to_inbox not in domain_mailboxes:
        # Rotate through mailboxes so we don't always use the same one
        to_inbox = random.choice(domain_mailboxes)

    subject = email_data.get("subject_line") or ""
    reply_subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"
    reply_body = random.choice(REPLY_SNIPPETS)

    if dry_run:
        return True, f"DRY: would reply from {to_inbox} to {from_email}"

    payload = {
        "from": to_inbox,
        "to": [from_email],
        "subject": reply_subject,
        "text_body": reply_body,
        "html_body": reply_body,
        "in_reply_to": msg_id,
    }

    try:
        r = session.post(f"{BASE_URL}/email", json=payload, timeout=30)
        if r.status_code in (200, 201):
            data = r.json()
            if data.get("sent") or data.get("id"):
                return True, "sent"
            return False, f"api response: {str(data)[:100]}"
        return False, f"http {r.status_code}: {r.text[:100]}"
    except Exception as e:
        return False, f"exception: {str(e)[:100]}"


def run_engagement_cycle(args, state, dead_domains, live_mailboxes):
    """Run one engagement cycle: fetch, filter, reply."""
    cycle_start = datetime.now()
    total_live = sum(len(v) for v in live_mailboxes.values())
    logger.info(f"=== Cycle start | {len(state['replied_ids'])} replied | {len(dead_domains)} dead domains | {total_live} live mailboxes across {len(live_mailboxes)} domains ===")

    emails = fetch_recent_inbound(max_pages=10)
    logger.info(f"Fetched {len(emails)} recent inbound emails")

    # Filter for warming emails we haven't replied to yet
    candidates = []
    skipped_real_lead = 0
    skipped_already = 0
    skipped_not_warming = 0

    for email in emails:
        msg_id = email.get("message_id")
        if not msg_id:
            continue
        if msg_id in state["replied_ids"]:
            skipped_already += 1
            continue
        if is_real_lead_email(email):
            skipped_real_lead += 1
            continue
        if not is_warming_email(email):
            skipped_not_warming += 1
            continue
        candidates.append(email)

    logger.info(
        f"Candidates: {len(candidates)} | "
        f"Skipped: {skipped_already} already replied, "
        f"{skipped_real_lead} real leads, {skipped_not_warming} not warming"
    )

    if not candidates:
        return 0, 0

    # Limit per cycle
    candidates = candidates[: args.limit]

    replied = 0
    failed = 0
    inboxes_used = set()

    for i, email in enumerate(candidates, 1):
        msg_id = email.get("message_id")
        to_inbox = email.get("to", [None])
        if isinstance(to_inbox, list):
            to_inbox = to_inbox[0]
        from_email = email.get("from_email", "?")
        subject = (email.get("subject_line") or "")[:50]

        success, reason = reply_to_warming_email(email, dead_domains, live_mailboxes, dry_run=args.dry_run)

        if success:
            state["replied_ids"].add(msg_id)
            state["total_sent"] = state.get("total_sent", 0) + (0 if args.dry_run else 1)
            replied += 1
            if to_inbox:
                inboxes_used.add(to_inbox)
            logger.info(f"  ✅ [{i}/{len(candidates)}] {to_inbox} <- {from_email}: {subject}")
        else:
            failed += 1
            logger.warning(f"  ❌ [{i}/{len(candidates)}] {to_inbox}: {reason}")

        # Save state every 5 replies for crash safety
        if replied % 5 == 0 and replied > 0:
            save_state(state)

        # Natural delay between replies
        if not args.dry_run and i < len(candidates):
            delay = random.uniform(args.min_delay, args.max_delay)
            time.sleep(delay)

    save_state(state)

    elapsed = (datetime.now() - cycle_start).total_seconds()
    logger.info(
        f"=== Cycle done in {elapsed:.0f}s | {replied} replied, {failed} failed | "
        f"{len(inboxes_used)} unique inboxes engaged ==="
    )

    return replied, failed


def main():
    parser = argparse.ArgumentParser(description="Warming engagement daemon")
    parser.add_argument("--daemon", action="store_true",
                        help="Run continuously (default: single run)")
    parser.add_argument("--interval", type=int, default=600,
                        help="Daemon poll interval in seconds (default: 600)")
    parser.add_argument("--limit", type=int, default=100,
                        help="Max replies per cycle (default: 100)")
    parser.add_argument("--min-delay", type=float, default=3.0,
                        help="Min seconds between replies (default: 3)")
    parser.add_argument("--max-delay", type=float, default=12.0,
                        help="Max seconds between replies (default: 12)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without sending")
    args = parser.parse_args()

    print("=" * 70)
    print(f"WARMING ENGAGEMENT BOT")
    print(f"Mode:     {'DAEMON' if args.daemon else 'SINGLE RUN'}")
    print(f"Dry-run:  {args.dry_run}")
    print(f"Interval: {args.interval}s" if args.daemon else "")
    print(f"Limit:    {args.limit} per cycle")
    print(f"Delay:    {args.min_delay}-{args.max_delay}s between replies")
    print("=" * 70)

    state = load_state()
    if state.get("last_run"):
        logger.info(f"Resuming from previous state | Total sent ever: {state.get('total_sent', 0)}")

    # Refresh dead domains + live mailboxes periodically
    dead_domains = get_dead_domains()
    live_mailboxes = get_live_mailboxes_by_domain()

    if not args.daemon:
        run_engagement_cycle(args, state, dead_domains, live_mailboxes)
        print(f"\nDone. Total sent ever: {state.get('total_sent', 0)}")
        return

    # Daemon mode
    cycle_count = 0
    refresh_every = 6  # Refresh dead domains + live mailboxes every N cycles
    while True:
        cycle_count += 1
        try:
            if cycle_count % refresh_every == 0:
                dead_domains = get_dead_domains()
                live_mailboxes = get_live_mailboxes_by_domain()
            run_engagement_cycle(args, state, dead_domains, live_mailboxes)
        except Exception as e:
            logger.error(f"Cycle {cycle_count} failed: {e}", exc_info=True)

        next_run = datetime.now() + timedelta(seconds=args.interval)
        logger.info(f"💤 Sleeping until {next_run.strftime('%H:%M:%S')} (cycle {cycle_count + 1})")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
