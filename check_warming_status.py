"""
Quick warming status checker for Mailreef truckice server.
Run periodically to track warming progress after DMARC fix.
"""
import os, sys, json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "mailreef_automation"))

import requests

api_key = os.environ["MAILREEF_API_KEY"]
base_url = "https://api.mailreef.com"
session = requests.Session()
session.auth = (api_key, "")
session.headers.update({"Content-Type": "application/json"})


def check_warming():
    print("=" * 60)
    print(f"WARMING STATUS CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # 1. Inbound warming volume (last 24h, last 7 days)
    print("\n📊 INBOUND WARMING VOLUME")
    print("-" * 40)
    now_ts = int(datetime.now().timestamp())
    day_ago = now_ts - 86400
    week_ago = now_ts - 604800

    total_last_24h = 0
    total_last_7d = 0
    inbox_hits_24h = {}

    page = 1
    done = False
    while not done and page <= 50:
        r = session.get(
            f"{base_url}/mail/inbound",
            params={"page": page, "display": 100},
            timeout=30,
        )
        if r.status_code != 200:
            break
        data = r.json()
        emails = data.get("data", data) if isinstance(data, dict) else data
        if not emails:
            break

        for e in emails:
            ts = e.get("ts", 0)
            if ts < week_ago:
                done = True
                break
            total_last_7d += 1
            if ts >= day_ago:
                total_last_24h += 1
                for recipient in e.get("to", []):
                    inbox_hits_24h[recipient] = inbox_hits_24h.get(recipient, 0) + 1

        page += 1

    print(f"  Last 24 hours: {total_last_24h} warming emails received")
    print(f"  Last 7 days:   {total_last_7d} warming emails received")
    if total_last_7d > 0:
        print(f"  Daily average:  {total_last_7d / 7:.1f}/day")

    if inbox_hits_24h:
        print(f"\n  Active inboxes (last 24h): {len(inbox_hits_24h)}")
        top = sorted(inbox_hits_24h.items(), key=lambda x: -x[1])[:5]
        for inbox, count in top:
            print(f"    {inbox}: {count}")

    # 2. Domain status summary
    print("\n📋 DOMAIN STATUS")
    print("-" * 40)
    domains = []
    page = 1
    while True:
        r = session.get(
            f"{base_url}/domains",
            params={"page": page, "display": 100},
            timeout=30,
        )
        data = r.json()
        batch = data.get("data", data) if isinstance(data, dict) else data
        if not batch:
            break
        domains.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    active = [d for d in domains if d.get("status") == "active"]
    stuck = [d for d in domains if d.get("status") != "active"]
    active_mboxes = sum(d.get("mailbox_count", 0) for d in active)
    stuck_mboxes = sum(d.get("mailbox_count", 0) for d in stuck)

    print(f"  Active domains: {len(active)} ({active_mboxes} inboxes)")
    if stuck:
        print(f"  Stuck domains:  {len(stuck)} ({stuck_mboxes} inboxes)")
        for d in stuck:
            print(f"    ❌ {d['id']} -> {d.get('status')}")

    # 3. Health verdict
    print("\n🏥 WARMING HEALTH")
    print("-" * 40)
    if total_last_24h >= active_mboxes:
        print("  ✅ HEALTHY - Warming volume looks good")
    elif total_last_24h >= active_mboxes * 0.3:
        print("  ⚠️  RAMPING UP - Volume increasing, check again tomorrow")
    elif total_last_24h > 0:
        print("  ⚠️  LOW VOLUME - Warming active but slow, give it 24-48h after DMARC fix")
    else:
        print("  ❌ NO WARMING - No warming emails in last 24h, check Mailreef dashboard")

    print()


if __name__ == "__main__":
    check_warming()
