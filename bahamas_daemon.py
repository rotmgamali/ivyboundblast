"""
Bahamas Retreat Lead Scraper — 24/7 Daemon

Continuously cycles through Florida + Southeast cities harvesting executive
contacts at small-to-mid B2B companies. Verifies via BulkEmailChecker. Writes
ONLY verified leads to the SQLite DB and (optionally) syncs to Google Sheets.

Runs forever in a loop with throttling between cycles to:
  - Avoid Google Maps rate limiting
  - Stay under BulkEmailChecker credit ceiling
  - Spread harvests across many cities for breadth

Usage:
    nohup /Users/mac/Ivybound/.venv/bin/python /Users/mac/Ivybound/bahamas_daemon.py \
        >> /Users/mac/Ivybound/logs/bahamas_daemon.log 2>&1 &

Stop:
    ps aux | grep bahamas_daemon | grep -v grep | awk '{print $2}' | xargs kill
"""
from __future__ import annotations
import argparse
import logging
import os
import random
import signal
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from lead_engine.db import HarvestDB
from lead_engine.email_verifier import EmailVerifier
from lead_engine.bulkemailchecker import BulkEmailChecker
from lead_engine.sheets_sync import sync_run

# Need to import harvest_city + run_harvest mechanics
from harvest import harvest_city

# ============================================================================
# Configuration
# ============================================================================
# Florida + Southeast cities — high-margin business hubs likely to host retreats.
CITIES = [
    # Florida (priority 1)
    "Miami FL", "Fort Lauderdale FL", "West Palm Beach FL", "Boca Raton FL",
    "Tampa FL", "Orlando FL", "Jacksonville FL", "Naples FL", "Sarasota FL",
    "Coral Gables FL", "Aventura FL", "Boynton Beach FL", "Delray Beach FL",
    "Stuart FL", "Vero Beach FL", "Fort Myers FL", "Clearwater FL",
    "St. Petersburg FL", "Gainesville FL", "Tallahassee FL",
    # Georgia (priority 2 — drivable to FL ports)
    "Atlanta GA", "Savannah GA", "Augusta GA", "Macon GA",
    # North Carolina (priority 3)
    "Charlotte NC", "Raleigh NC", "Durham NC", "Wilmington NC",
    # South Carolina
    "Charleston SC", "Greenville SC", "Columbia SC",
    # Alabama
    "Birmingham AL", "Huntsville AL", "Mobile AL",
    # Tennessee (high-net-worth shoulder)
    "Nashville TN", "Memphis TN", "Knoxville TN",
]

# Cycle settings
MAX_PER_CITY = 30                     # Maps results per city per cycle
SLEEP_BETWEEN_CITIES_SEC = (90, 240)  # Random delay range
SLEEP_BETWEEN_FULL_CYCLES_SEC = 3600  # 1 hour rest between full sweeps
CITIES_PER_CYCLE = 4                  # Process this many cities per cycle, then sleep
CREDIT_FLOOR = 500                    # Pause if BulkEmailChecker credits drop below this

# ============================================================================
# Logging
# ============================================================================
os.makedirs("/Users/mac/Ivybound/logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/Users/mac/Ivybound/logs/bahamas_daemon.log"),
    ],
)
logger = logging.getLogger("bahamas_daemon")

_shutdown = False
def _handle_sigterm(signum, frame):
    global _shutdown
    _shutdown = True
    logger.info(f"Received signal {signum}, shutting down gracefully after current city...")

signal.signal(signal.SIGTERM, _handle_sigterm)
signal.signal(signal.SIGINT, _handle_sigterm)


def get_total_verified_count(db: HarvestDB) -> int:
    """Count total verified contacts across all bahamas runs in DB."""
    conn = db._get_conn()
    return conn.execute("""
        SELECT COUNT(*) FROM contacts c
        JOIN businesses b ON c.business_id = b.id
        WHERE b.niche = 'executives' AND c.email_status IN ('verified', 'catch_all')
    """).fetchone()[0]


def run_cycle(args, db: HarvestDB, verifier: EmailVerifier,
              paid_verifier: BulkEmailChecker, cities_to_process: list) -> dict:
    """Run one harvest cycle across the selected cities."""
    # Create a single run for this cycle covering all cities
    run_id = db.create_run("executives", ", ".join(cities_to_process))
    cycle_stats = {"businesses": 0, "contacts": 0, "verified": 0}

    for city in cities_to_process:
        if _shutdown:
            break

        # Credit check
        credits = paid_verifier.credits_remaining()
        if credits is not None and credits < CREDIT_FLOOR:
            logger.warning(f"⚠️  BulkEmailChecker credits at {credits} (below floor {CREDIT_FLOOR}). Pausing.")
            return cycle_stats

        try:
            stats = harvest_city(
                city=city, niche="executives", run_id=run_id,
                max_per_city=args.max_per_city, db=db,
                verifier=verifier, paid_verifier=paid_verifier
            )
            for k in cycle_stats:
                cycle_stats[k] += stats.get(k, 0)
            logger.info(
                f"[{city}] +{stats.get('businesses', 0)} biz, "
                f"+{stats.get('contacts', 0)} contacts ({stats.get('verified', 0)} verified)"
            )
        except Exception as e:
            logger.error(f"[{city}] failed: {e}", exc_info=True)

        # Random delay between cities
        if not _shutdown and city != cities_to_process[-1]:
            delay = random.uniform(*SLEEP_BETWEEN_CITIES_SEC)
            logger.info(f"💤 Sleeping {delay:.0f}s before next city")
            time.sleep(delay)

    db.complete_run(run_id)
    return cycle_stats


def run_daemon(args):
    db = HarvestDB()
    verifier = EmailVerifier()
    paid_verifier = BulkEmailChecker()

    cities = list(args.cities) if args.cities else CITIES
    logger.info("=" * 70)
    logger.info(f"BAHAMAS RETREAT DAEMON STARTED")
    logger.info(f"  Cities pool: {len(cities)} cities")
    logger.info(f"  Max per city: {args.max_per_city}")
    logger.info(f"  Cities per cycle: {args.cities_per_cycle}")
    logger.info(f"  Credit floor: {CREDIT_FLOOR}")
    logger.info(f"  Cycle rest: {args.cycle_rest_min} min")
    logger.info("=" * 70)

    cycle_num = 0
    city_queue = []

    while not _shutdown:
        cycle_num += 1
        cycle_start = datetime.now()

        # Refill the queue with shuffled cities when empty
        if not city_queue:
            city_queue = list(cities)
            random.shuffle(city_queue)
            logger.info(f"🔄 New full sweep — {len(city_queue)} cities queued (shuffled)")

        # Take next batch of cities
        batch = city_queue[:args.cities_per_cycle]
        city_queue = city_queue[args.cities_per_cycle:]

        logger.info(f"\n=== Cycle #{cycle_num} | {len(batch)} cities ===")
        try:
            stats = run_cycle(args, db, verifier, paid_verifier, batch)
        except Exception as e:
            logger.error(f"Cycle #{cycle_num} crashed: {e}", exc_info=True)
            stats = {}

        # Status summary
        elapsed = (datetime.now() - cycle_start).total_seconds()
        total_verified = get_total_verified_count(db)
        credits = paid_verifier.credits_remaining()
        logger.info(
            f"=== Cycle #{cycle_num} done in {elapsed:.0f}s | "
            f"+{stats.get('verified', 0)} verified this cycle | "
            f"{total_verified} total verified | "
            f"{credits} credits left ==="
        )

        if _shutdown:
            break

        # Sheets sync after every cycle (best-effort)
        if args.auto_sync_sheets and stats.get("verified", 0) > 0:
            try:
                # Sync the most recent run that has unsynced contacts
                conn = db._get_conn()
                latest_run = conn.execute(
                    "SELECT id FROM runs WHERE niche='executives' ORDER BY id DESC LIMIT 1"
                ).fetchone()
                if latest_run:
                    synced = sync_run(latest_run["id"], db, sheet_name=args.sheet_name)
                    logger.info(f"📤 Synced {synced} contacts to Sheet '{args.sheet_name}'")
            except Exception as e:
                logger.warning(f"Sheet sync failed: {e}")

        # Rest between cycles
        if not _shutdown and city_queue:
            # Short rest mid-sweep
            short_rest = 60 * 5
            logger.info(f"💤 Mid-sweep rest: {short_rest}s")
            time.sleep(short_rest)
        elif not _shutdown:
            # Long rest at end of sweep
            rest = args.cycle_rest_min * 60
            logger.info(f"💤 Full-sweep complete. Resting {args.cycle_rest_min}min before next sweep")
            time.sleep(rest)

    logger.info("Daemon stopped.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-per-city", type=int, default=MAX_PER_CITY,
                        help="Max Maps results per city per cycle")
    parser.add_argument("--cities-per-cycle", type=int, default=CITIES_PER_CYCLE,
                        help="Cities to process before mid-sweep rest")
    parser.add_argument("--cycle-rest-min", type=int, default=60,
                        help="Minutes to rest after a full city sweep")
    parser.add_argument("--cities", nargs="*", default=None,
                        help="Override the default city list")
    parser.add_argument("--auto-sync-sheets", action="store_true",
                        help="Auto-sync verified contacts to Google Sheets after each cycle")
    parser.add_argument("--sheet-name", default="Bahamas Retreat - Campaign Leads",
                        help="Google Sheet name to sync to")
    parser.add_argument("--once", action="store_true",
                        help="Run a single cycle and exit (for testing)")
    args = parser.parse_args()

    if args.once:
        # Run only one cycle
        global _shutdown
        db = HarvestDB()
        verifier = EmailVerifier()
        paid_verifier = BulkEmailChecker()
        cities = (args.cities or CITIES)[:args.cities_per_cycle]
        logger.info(f"Single-cycle run on cities: {cities}")
        run_cycle(args, db, verifier, paid_verifier, cities)
        return

    run_daemon(args)


if __name__ == "__main__":
    main()
