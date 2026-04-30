#!/usr/bin/env python3
"""
Universal Lead Generation Engine
Finds and verifies business contacts in any niche using Google Maps + website crawling.

Usage:
    python harvest.py --niche "dentists" --cities "Miami FL,Tampa FL" --max-per-city 100
    python harvest.py --niche "private schools" --states "FL,TX" --max-per-city 50
    python harvest.py --niche "accountants" --cities-file cities.txt
    python harvest.py --list-runs
    python harvest.py --export-csv 1
    python harvest.py --sync-sheets 1
"""
import argparse
import logging
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lead_engine.db import HarvestDB
from lead_engine.scraper import search_maps
from lead_engine.bahamas_scraper import search_maps_free
from lead_engine.website_crawler import extract_contacts
from lead_engine.email_verifier import EmailVerifier
from lead_engine.bulkemailchecker import BulkEmailChecker
from lead_engine.contact_scorer import select_top_contacts
from lead_engine.niches import get_niche_config, US_STATE_CITIES
from lead_engine.sheets_sync import sync_run

# Niches that should use the FREE Playwright Maps scraper rather than Apify.
FREE_SCRAPER_NICHES = {"executives"}

# Niches that should use the paid BulkEmailChecker for accurate verification.
# All other niches use the local DNS+catchall verifier.
PAID_VERIFY_NICHES = {"executives"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)s] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("harvest.log"),
    ]
)
logger = logging.getLogger("harvest")

# Limit concurrent Apify API calls to avoid rate limits
apify_semaphore = threading.Semaphore(3)


def harvest_city(city: str, niche: str, run_id: int, max_per_city: int,
                 db: HarvestDB, verifier: EmailVerifier,
                 paid_verifier: Optional[BulkEmailChecker] = None) -> dict:
    """Worker function: harvest all businesses for one city + niche."""
    config = get_niche_config(niche)
    stats = {"city": city, "businesses": 0, "contacts": 0, "verified": 0}
    use_paid = niche.lower().strip() in PAID_VERIFY_NICHES and paid_verifier is not None

    # 1. Search Google Maps — use the FREE Playwright scraper for niches
    # that opt out of paid Apify (e.g. "executives" for the Bahamas Retreat
    # campaign), otherwise fall back to the Apify-backed scraper.
    if niche.lower().strip() in FREE_SCRAPER_NICHES:
        businesses = search_maps_free(
            niche=niche, city=city,
            max_results=max_per_city,
            search_variations=config.search_variations,
        )
    else:
        with apify_semaphore:
            businesses = search_maps(
                niche=niche, city=city,
                max_results=max_per_city,
                search_variations=config.search_variations
            )

    logger.info(f"[{city}] Found {len(businesses)} businesses from Maps")

    for biz in businesses:
        # Institution guard
        biz_name_lower = biz.get("name", "").lower()
        if any(guard in biz_name_lower for guard in config.institution_guard):
            continue

        # 2. Insert business
        business_id = db.insert_business(run_id, biz)
        if not business_id:
            continue
        stats["businesses"] += 1

        # 3. Extract contacts from website
        all_contacts = list(biz.get("raw_emails", []))
        if biz.get("website"):
            crawled = extract_contacts(biz["website"], niche)
            # Merge crawled emails with Apify emails
            crawled_emails = crawled.get("emails", [])
            crawled_contacts = crawled.get("contacts", [])

            for email in crawled_emails:
                if not any(c.get("email") == email for c in all_contacts):
                    all_contacts.append({"email": email, "title": ""})

            for contact in crawled_contacts:
                if contact.get("email") and not any(c.get("email") == contact["email"] for c in all_contacts):
                    all_contacts.append(contact)

        # 3b. Generate synthetic email candidates if website crawling found nothing.
        # Most B2B sites hide exec emails — but companies usually have generic
        # boxes (info@, contact@) that route to a real human. Verifier filters duds.
        if niche.lower().strip() == "executives" and not all_contacts and biz.get("website"):
            from urllib.parse import urlparse as _urlp
            try:
                host = _urlp(biz["website"]).netloc.lower()
                if host.startswith("www."):
                    host = host[4:]
                if host and "." in host:
                    for prefix in ("info", "contact", "hello", "team", "office"):
                        all_contacts.append({
                            "email": f"{prefix}@{host}",
                            "name": "",
                            "title": "",  # Empty title → email_generator falls back to "To the {company} Team,"
                            "synthetic": True,
                        })
            except Exception:
                pass

        # 4. Verify emails (paid BulkEmailChecker for executives, DNS for others)
        for contact in all_contacts:
            email = contact.get("email", "")
            if not email:
                continue
            if use_paid:
                bec_result = paid_verifier.verify(email)
                # Map BEC status to our internal vocab so downstream code is unchanged.
                if bec_result.status == "passed":
                    contact["email_status"] = "verified"
                elif bec_result.status == "unknown" and bec_result.is_catchall:
                    contact["email_status"] = "catch_all"
                elif bec_result.is_disposable:
                    contact["email_status"] = "disposable"
                else:
                    contact["email_status"] = "invalid"
                contact["mx_host"] = ""
                contact["is_catch_all"] = bec_result.is_catchall
                contact["bec_event"] = bec_result.event
                contact["bec_role_account"] = bec_result.is_role_account
            else:
                result = verifier.verify(email)
                contact["email_status"] = result.status
                contact["mx_host"] = result.mx_host
                contact["is_catch_all"] = result.is_catch_all

        # 5. Score and select top contacts. For executives, only keep ones
        # that the paid verifier actually confirmed deliverable — bypass the
        # title-based scorer (which rejects `info@`, `contact@` etc.) since
        # for small B2B those generic boxes route directly to founders.
        if niche.lower().strip() == "executives":
            top = [c for c in all_contacts
                   if c.get("email_status") in ("verified", "catch_all")
                   and c.get("email")]
            # Limit to 3 best per business
            top = sorted(top, key=lambda c: 0 if c.get("email_status") == "verified" else 1)[:3]
        else:
            top = select_top_contacts(all_contacts, niche, max_contacts=3)

        # 6. Insert contacts
        for contact in top:
            # Parse name
            name = contact.get("name", "")
            first_name = ""
            last_name = ""
            if name:
                parts = name.split()
                first_name = parts[0] if parts else ""
                last_name = parts[-1] if len(parts) > 1 else ""

            db.insert_contact(business_id, {
                "email": contact.get("email", ""),
                "first_name": first_name,
                "last_name": last_name,
                "title": contact.get("title", ""),
                "seniority_score": contact.get("seniority_score", 0),
                "email_status": contact.get("email_status", "unknown"),
                "mx_host": contact.get("mx_host", ""),
                "is_catch_all": contact.get("is_catch_all", False),
            })
            stats["contacts"] += 1
            if contact.get("email_status") == "verified":
                stats["verified"] += 1

    logger.info(f"[{city}] Done: {stats['businesses']} businesses, {stats['contacts']} contacts ({stats['verified']} verified)")
    return stats


def resolve_cities(args) -> list:
    """Resolve --cities, --states, --cities-file into a list of city strings."""
    cities = []

    if args.cities:
        cities.extend([c.strip() for c in args.cities.split(",")])

    if args.states:
        for state in args.states.split(","):
            state = state.strip().upper()
            state_cities = US_STATE_CITIES.get(state, [])
            for city in state_cities:
                cities.append(f"{city} {state}")

    if args.cities_file:
        with open(args.cities_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    cities.append(line)

    return cities


def run_harvest(args):
    """Main harvest execution."""
    db = HarvestDB()
    verifier = EmailVerifier()
    # Lazy paid verifier — only constructed if needed (raises if key missing).
    paid_verifier = None
    if args.niche.lower().strip() in PAID_VERIFY_NICHES:
        try:
            paid_verifier = BulkEmailChecker()
            logger.info("Paid verifier active (BulkEmailChecker)")
        except Exception as e:
            logger.warning(f"Paid verifier unavailable, falling back to DNS: {e}")
    cities = resolve_cities(args)

    if not cities:
        logger.error("No cities specified. Use --cities, --states, or --cities-file")
        return

    niche = args.niche
    max_per_city = args.max_per_city

    logger.info(f"Starting harvest: niche='{niche}', cities={len(cities)}, max_per_city={max_per_city}")
    logger.info(f"Cities: {', '.join(cities[:10])}{'...' if len(cities) > 10 else ''}")

    run_id = db.create_run(niche, ", ".join(cities))
    start_time = time.time()

    total_stats = {"businesses": 0, "contacts": 0, "verified": 0}

    with ThreadPoolExecutor(max_workers=10, thread_name_prefix="harvest") as executor:
        futures = {
            executor.submit(harvest_city, city, niche, run_id, max_per_city, db, verifier, paid_verifier): city
            for city in cities
        }

        for future in as_completed(futures):
            city = futures[future]
            try:
                result = future.result()
                total_stats["businesses"] += result["businesses"]
                total_stats["contacts"] += result["contacts"]
                total_stats["verified"] += result["verified"]
            except Exception as e:
                logger.error(f"Worker failed for {city}: {e}")

    db.complete_run(run_id)
    elapsed = time.time() - start_time

    print(f"\n{'=' * 60}")
    print(f"HARVEST COMPLETE — Run #{run_id}")
    print(f"{'=' * 60}")
    print(f"Niche:      {niche}")
    print(f"Cities:     {len(cities)}")
    print(f"Time:       {elapsed:.1f}s")
    print(f"Businesses: {total_stats['businesses']}")
    print(f"Contacts:   {total_stats['contacts']}")
    print(f"Verified:   {total_stats['verified']}")
    print(f"{'=' * 60}")
    print(f"\nNext steps:")
    print(f"  python harvest.py --export-csv {run_id}")
    print(f"  python harvest.py --sync-sheets {run_id}")


def list_runs(db: HarvestDB):
    runs = db.get_all_runs()
    if not runs:
        print("No harvest runs found.")
        return
    print(f"\n{'ID':>4}  {'Niche':<20}  {'Status':<10}  {'Businesses':>10}  {'Contacts':>10}  {'Started':<20}")
    print("-" * 85)
    for r in runs:
        print(f"{r['id']:>4}  {r['niche']:<20}  {r['status']:<10}  {r['total_businesses']:>10}  {r['total_contacts']:>10}  {str(r['started_at']):<20}")


def export_csv(run_id: int, db: HarvestDB):
    os.makedirs("exports", exist_ok=True)
    stats = db.get_run_stats(run_id)
    if not stats:
        print(f"Run {run_id} not found")
        return
    filename = f"exports/run_{run_id}_{stats['niche'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv"
    count = db.export_run_csv(run_id, filename)
    print(f"Exported {count} contacts to {filename}")


def main():
    parser = argparse.ArgumentParser(description="Universal Lead Generation Engine")

    # Harvest mode
    parser.add_argument("--niche", type=str, help="Business niche to search (e.g. 'dentists', 'private schools')")
    parser.add_argument("--cities", type=str, help="Comma-separated cities (e.g. 'Miami FL,Tampa FL')")
    parser.add_argument("--states", type=str, help="Comma-separated state codes (e.g. 'FL,TX,CA')")
    parser.add_argument("--cities-file", type=str, help="Path to file with one city per line")
    parser.add_argument("--max-per-city", type=int, default=100, help="Max results per city (default: 100)")

    # Utility mode
    parser.add_argument("--list-runs", action="store_true", help="List all harvest runs")
    parser.add_argument("--export-csv", type=int, metavar="RUN_ID", help="Export a run to CSV")
    parser.add_argument("--sync-sheets", type=int, metavar="RUN_ID", help="Sync a run to Google Sheets")
    parser.add_argument("--sheet-name", type=str, help="Custom Google Sheet name for sync")

    args = parser.parse_args()
    db = HarvestDB()

    if args.list_runs:
        list_runs(db)
    elif args.export_csv:
        export_csv(args.export_csv, db)
    elif args.sync_sheets:
        sync_run(args.sync_sheets, db, sheet_name=args.sheet_name)
    elif args.niche:
        run_harvest(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
