"""
Smartlead Sync: Connect all Mailreef inboxes to Smartlead for warming.

Pulls live inboxes from both Mailreef servers (truckice + competitionhand),
adds them to Smartlead via API, and enables warmup with gradual ramp-up.

Usage:
    python3 smartlead_sync.py --sync              # Add missing accounts + enable warmup
    python3 smartlead_sync.py --delete-stale      # Remove old dead-server accounts
    python3 smartlead_sync.py --status            # Show current state
    python3 smartlead_sync.py --all               # Delete stale + sync + enable warmup
"""
import os
import sys
import time
import json
import argparse
import logging
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import requests

MAILREEF_API_KEY = os.environ["MAILREEF_API_KEY"]
SMARTLEAD_API_KEY = os.environ["SMARTLEAD_API_KEY"]

MR_BASE = "https://api.mailreef.com"
SL_BASE = "https://server.smartlead.ai/api/v1"

mr = requests.Session()
mr.auth = (MAILREEF_API_KEY, "")
mr.headers.update({"Content-Type": "application/json"})

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("smartlead_sync.log")],
)
logger = logging.getLogger("smartlead_sync")


def fetch_mailreef_inboxes():
    """Pull all live inboxes with credentials from both Mailreef servers."""
    inboxes = []
    for server in ["truckice", "competitionhand"]:
        logger.info(f"Fetching {server} inboxes...")
        page = 1
        server_count = 0
        while True:
            r = mr.get(
                f"{MR_BASE}/mailboxes",
                params={"page": page, "display": 100, "server": server},
                timeout=30,
            )
            if r.status_code != 200:
                break
            batch = r.json().get("data", [])
            if not batch:
                break
            for m in batch:
                if m.get("live"):
                    # Get full details for password
                    mbox_id = m.get("id")
                    try:
                        detail = mr.get(f"{MR_BASE}/mailboxes/{mbox_id}", timeout=20).json()
                        inboxes.append({
                            "email": mbox_id,
                            "sender_name": detail.get("sender_name", "Web4Guru Team"),
                            "smtp_host": detail.get("smtp_host", f"smtp.{server}.com"),
                            "imap_host": detail.get("imap_host", f"imap.{server}.com"),
                            "password": detail.get("password"),
                            "server": server,
                        })
                        server_count += 1
                    except Exception as e:
                        logger.warning(f"Could not fetch details for {mbox_id}: {e}")
            if len(batch) < 100:
                break
            page += 1
        logger.info(f"  {server}: {server_count} live inboxes collected")
    return inboxes


def fetch_smartlead_accounts():
    """Fetch all accounts from Smartlead."""
    accounts = []
    offset = 0
    while True:
        r = requests.get(
            f"{SL_BASE}/email-accounts",
            params={"api_key": SMARTLEAD_API_KEY, "offset": offset, "limit": 100},
            timeout=30,
        )
        if r.status_code != 200:
            logger.error(f"Smartlead fetch error: {r.status_code} {r.text[:200]}")
            break
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        accounts.extend(batch)
        if len(batch) < 100:
            break
        offset += 100
    return accounts


def delete_stale_accounts():
    """Delete Smartlead accounts pointing to dead servers (birdsgeese, errorskin)."""
    accounts = fetch_smartlead_accounts()
    stale = []
    for a in accounts:
        smtp_host = (a.get("smtp_host") or "").lower()
        if "birdsgeese" in smtp_host or "errorskin" in smtp_host:
            stale.append(a)

    logger.info(f"Found {len(stale)} stale accounts (birdsgeese/errorskin)")

    deleted = 0
    failed = 0
    for i, a in enumerate(stale, 1):
        email = a.get("from_email", "?")
        account_id = a.get("id")
        try:
            r = requests.delete(
                f"{SL_BASE}/email-accounts/{account_id}",
                params={"api_key": SMARTLEAD_API_KEY},
                timeout=30,
            )
            if r.status_code in (200, 204):
                deleted += 1
                logger.info(f"  [{i}/{len(stale)}] 🗑️  Deleted {email}")
            else:
                failed += 1
                logger.warning(f"  [{i}/{len(stale)}] ❌ Delete failed {email}: {r.status_code} {r.text[:100]}")
        except Exception as e:
            failed += 1
            logger.warning(f"  [{i}/{len(stale)}] ❌ {email}: {e}")
        time.sleep(0.3)

    logger.info(f"Deleted: {deleted}, Failed: {failed}")
    return deleted


def upsert_account(inbox, existing_id=None):
    """Create or update a Smartlead account with Mailreef inbox credentials."""
    payload = {
        "id": existing_id,
        "from_name": inbox["sender_name"],
        "from_email": inbox["email"],
        "user_name": inbox["email"],
        "password": inbox["password"],
        "smtp_host": inbox["smtp_host"],
        "smtp_port": 465,
        "imap_host": inbox["imap_host"],
        "imap_port": 993,
        "max_email_per_day": 25,
        "custom_tracking_url": "",
        "bcc": "",
        "signature": "",
        "warmup_enabled": True,
        "total_warmup_per_day": 25,
        "daily_rampup": 2,
        "reply_rate_percentage": 50,
    }
    try:
        r = requests.post(
            f"{SL_BASE}/email-accounts/save",
            params={"api_key": SMARTLEAD_API_KEY},
            json=payload,
            timeout=60,
        )
        if r.status_code in (200, 201):
            data = r.json()
            account_id = data.get("emailAccountId") or data.get("id") or existing_id
            action = "updated" if existing_id else "created"
            return True, account_id, action
        return False, None, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, None, str(e)[:200]


def enable_warmup(account_id, total_per_day=25, ramp=2, reply_rate=50):
    """Enable warmup on an account with optimal settings."""
    payload = {
        "warmup_enabled": True,
        "total_warmup_per_day": total_per_day,
        "daily_rampup": ramp,
        "reply_rate_percentage": reply_rate,
        "warmup_key_id": f"ivy-{account_id}",
    }
    try:
        r = requests.post(
            f"{SL_BASE}/email-accounts/{account_id}/warmup",
            params={"api_key": SMARTLEAD_API_KEY},
            json=payload,
            timeout=30,
        )
        return r.status_code in (200, 201), r.text[:200]
    except Exception as e:
        return False, str(e)[:200]


def sync_inboxes():
    """Sync all Mailreef inboxes to Smartlead (create or update as needed)."""
    logger.info("=" * 70)
    logger.info("STEP 1: Pulling Mailreef inboxes")
    logger.info("=" * 70)
    mr_inboxes = fetch_mailreef_inboxes()
    logger.info(f"Total live Mailreef inboxes: {len(mr_inboxes)}")

    logger.info("")
    logger.info("=" * 70)
    logger.info("STEP 2: Fetching existing Smartlead accounts")
    logger.info("=" * 70)
    sl_accounts = fetch_smartlead_accounts()
    # Build a map: lowercase email -> account_id
    email_to_id = {
        a.get("from_email", "").lower(): a.get("id")
        for a in sl_accounts
        if a.get("from_email")
    }
    logger.info(f"Existing Smartlead accounts: {len(sl_accounts)}")

    # Classify each Mailreef inbox: update-existing or create-new
    to_update = []
    to_create = []
    for inbox in mr_inboxes:
        email_lower = inbox["email"].lower()
        if email_lower in email_to_id:
            to_update.append((inbox, email_to_id[email_lower]))
        else:
            to_create.append(inbox)

    logger.info(f"To update (with fresh creds): {len(to_update)}")
    logger.info(f"To create (new accounts):    {len(to_create)}")

    logger.info("")
    logger.info("=" * 70)
    logger.info(f"STEP 3: Upserting {len(mr_inboxes)} accounts")
    logger.info("=" * 70)

    updated = 0
    created = 0
    failed = 0

    # Process updates first (faster, just refreshing credentials)
    all_work = [(i, eid) for i, eid in to_update] + [(i, None) for i in to_create]
    total = len(all_work)

    for i, (inbox, existing_id) in enumerate(all_work, 1):
        email = inbox["email"]
        success, account_id, action = upsert_account(inbox, existing_id=existing_id)
        if success:
            if action == "updated":
                updated += 1
            else:
                created += 1
            marker = "🔄" if action == "updated" else "➕"
            logger.info(f"  [{i}/{total}] {marker} {email} (id={account_id}) — {inbox['server']}")
        else:
            failed += 1
            logger.warning(f"  [{i}/{total}] ❌ {email}: {action}")
        time.sleep(0.5)

    logger.info("")
    logger.info("=" * 70)
    logger.info(f"SYNC COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Updated: {updated}")
    logger.info(f"Created: {created}")
    logger.info(f"Failed:  {failed}")


def show_status():
    """Show current Smartlead account status."""
    accounts = fetch_smartlead_accounts()
    logger.info(f"Total Smartlead accounts: {len(accounts)}")

    by_server = {}
    warmup_status = {}
    for a in accounts:
        host = (a.get("smtp_host") or "").lower()
        if "truckice" in host:
            srv = "truckice"
        elif "competitionhand" in host:
            srv = "competitionhand"
        elif "birdsgeese" in host:
            srv = "birdsgeese (DEAD)"
        elif "errorskin" in host:
            srv = "errorskin (DEAD)"
        else:
            srv = host or "unknown"
        by_server[srv] = by_server.get(srv, 0) + 1

        wd = a.get("warmup_details") or {}
        status = wd.get("status", "NOT_SET") if isinstance(wd, dict) else "NOT_SET"
        warmup_status[status] = warmup_status.get(status, 0) + 1

    print("\nBY SERVER:")
    for s, c in sorted(by_server.items()):
        print(f"  {s}: {c}")

    print("\nWARMUP STATUS:")
    for s, c in warmup_status.items():
        print(f"  {s}: {c}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sync", action="store_true", help="Add missing Mailreef inboxes to Smartlead")
    parser.add_argument("--delete-stale", action="store_true", help="Delete old birdsgeese/errorskin accounts")
    parser.add_argument("--status", action="store_true", help="Show current Smartlead state")
    parser.add_argument("--all", action="store_true", help="Delete stale + sync new inboxes")
    args = parser.parse_args()

    if args.all:
        delete_stale_accounts()
        sync_inboxes()
        show_status()
    elif args.delete_stale:
        delete_stale_accounts()
    elif args.sync:
        sync_inboxes()
    elif args.status:
        show_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
