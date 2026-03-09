"""
Continuous Lead Generation Pipeline — State-by-State Rotation

Strategy:
  1. Exhaust every city in Texas first (all school types per city)
  2. Move to the next state alphabetically
  3. After completing all 50 states, circle back to Texas
  4. Progress is persisted in SQLite so container restarts don't lose position

Duplicate Prevention:
  - The google_maps_scraper already deduplicates by domain/email/business name
  - SQLite tracks completed (state, city, school_type) combos to avoid re-running queries
"""

import os
import sys
import time
import random
import logging
import subprocess
import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from sheets_integration import GoogleSheetsClient
from pipeline.us_states_cities import STATES_CITIES, STATE_ORDER, STATE_ABBREV

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - LEAD_GEN - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('lead_generator.log')
    ]
)
logger = logging.getLogger(__name__)

MAX_LEAD_LIMIT = 50000
SHEET_NAME = "Ivy Bound - Scraped Leads"
PIPELINE_DIR = Path(__file__).resolve().parent
SCRAPER_SCRIPT = PIPELINE_DIR / "google_maps_scraper.py"
PROGRESS_DB = BASE_DIR / "scraper_progress.db"

SCHOOL_TYPES = [
    "Private schools",
    "Public high schools",
    "Middle schools",
    "Elementary schools",
    "Charter schools",
    "Montessori schools",
    "Christian schools",
    "Catholic schools",
    "Preparatory schools",
]


class ScrapeProgressTracker:
    """SQLite-backed progress tracker that survives container restarts."""
    
    def __init__(self, db_path=PROGRESS_DB):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self._init_db()
    
    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS completed_queries (
                state TEXT NOT NULL,
                city TEXT NOT NULL,
                school_type TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                PRIMARY KEY (state, city, school_type)
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS state_progress (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                current_state_index INTEGER NOT NULL DEFAULT 0,
                current_cycle INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            )
        """)
        # Insert default row if not present
        self.conn.execute("""
            INSERT OR IGNORE INTO state_progress (id, current_state_index, current_cycle, updated_at)
            VALUES (1, 0, 1, ?)
        """, (datetime.utcnow().isoformat(),))
        self.conn.commit()
    
    def is_completed(self, state: str, city: str, school_type: str) -> bool:
        cursor = self.conn.execute(
            "SELECT 1 FROM completed_queries WHERE state=? AND city=? AND school_type=?",
            (state, city, school_type)
        )
        return cursor.fetchone() is not None
    
    def mark_completed(self, state: str, city: str, school_type: str):
        self.conn.execute(
            "INSERT OR IGNORE INTO completed_queries (state, city, school_type, completed_at) VALUES (?, ?, ?, ?)",
            (state, city, school_type, datetime.utcnow().isoformat())
        )
        self.conn.commit()
    
    def get_state_progress(self) -> dict:
        cursor = self.conn.execute("SELECT current_state_index, current_cycle FROM state_progress WHERE id=1")
        row = cursor.fetchone()
        return {"state_index": row[0], "cycle": row[1]}
    
    def advance_state(self, new_index: int, cycle: int):
        self.conn.execute(
            "UPDATE state_progress SET current_state_index=?, current_cycle=?, updated_at=? WHERE id=1",
            (new_index, cycle, datetime.utcnow().isoformat())
        )
        self.conn.commit()
    
    def get_state_stats(self, state: str) -> dict:
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM completed_queries WHERE state=?", (state,)
        )
        completed = cursor.fetchone()[0]
        total = len(STATES_CITIES.get(state, [])) * len(SCHOOL_TYPES)
        return {"completed": completed, "total": total, "remaining": total - completed}
    
    def get_remaining_queries(self, state: str) -> list:
        """Get all (city, school_type) combos not yet completed for a state."""
        remaining = []
        cities = STATES_CITIES.get(state, [])
        for city in cities:
            for school_type in SCHOOL_TYPES:
                if not self.is_completed(state, city, school_type):
                    remaining.append((city, school_type))
        return remaining
    
    def reset_state(self, state: str):
        """Reset all progress for a specific state (for re-scraping on next cycle)."""
        self.conn.execute("DELETE FROM completed_queries WHERE state=?", (state,))
        self.conn.commit()


def get_current_lead_count() -> int:
    try:
        client = GoogleSheetsClient(input_sheet_name=SHEET_NAME)
        client.setup_sheets()
        records = client._fetch_all_records()
        return len(records)
    except Exception as e:
        logger.error(f"Failed to check sheet count: {e}")
        return 0


def run_pipeline(test_run: bool = False):
    logger.info("=" * 60)
    logger.info("🚀 STARTING STATE-BY-STATE LEAD GENERATION PIPELINE")
    logger.info("=" * 60)
    
    tracker = ScrapeProgressTracker()
    progress = tracker.get_state_progress()
    state_idx = progress["state_index"]
    cycle = progress["cycle"]
    
    logger.info(f"📍 Resuming at state index {state_idx} ({STATE_ORDER[state_idx]}), Cycle {cycle}")
    
    while True:
        # Get current state
        current_state = STATE_ORDER[state_idx]
        state_abbrev = STATE_ABBREV[current_state]
        stats = tracker.get_state_stats(current_state)
        
        logger.info(f"")
        logger.info(f"{'='*60}")
        logger.info(f"📍 STATE: {current_state} ({state_abbrev}) — Cycle {cycle}")
        logger.info(f"📊 Progress: {stats['completed']}/{stats['total']} queries done, {stats['remaining']} remaining")
        logger.info(f"{'='*60}")
        
        # Get remaining queries for this state
        remaining = tracker.get_remaining_queries(current_state)
        
        if not remaining:
            logger.info(f"✅ {current_state} COMPLETE — All {stats['total']} queries finished!")
            
            # Move to next state
            state_idx += 1
            if state_idx >= len(STATE_ORDER):
                # Completed ALL 50 states — start a new cycle
                cycle += 1
                state_idx = 0
                logger.info(f"🔄 ALL 50 STATES COMPLETE! Starting Cycle {cycle}...")
                
                # Reset all progress for the new cycle so we re-scrape everything
                for state in STATE_ORDER:
                    tracker.reset_state(state)
            
            tracker.advance_state(state_idx, cycle)
            continue
        
        # 1. Check lead limit
        current_leads = get_current_lead_count()
        logger.info(f"📈 Current lead count in sheet: {current_leads} / {MAX_LEAD_LIMIT}")
        
        if current_leads >= MAX_LEAD_LIMIT:
            logger.warning(f"Lead limit reached ({MAX_LEAD_LIMIT}). Pausing generator for 6 hours.")
            time.sleep(60 * 60 * 6)
            continue
        
        # 2. Build batch of queries (up to 5 at a time)
        batch_size = min(5, len(remaining))
        batch = remaining[:batch_size]
        
        queries = []
        for city, school_type in batch:
            queries.append(f"{school_type} in {city}, {state_abbrev}")
        
        batch_query_string = " | ".join(queries)
        
        logger.info(f"🔍 Batch ({len(queries)} queries): {batch_query_string}")
        start_time = time.time()
        
        # 3. Run scraper subprocess
        try:
            cmd = [
                sys.executable, "-u", str(SCRAPER_SCRIPT),
                "--queries", batch_query_string,
                "--sheet-name", SHEET_NAME
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(PIPELINE_DIR)
            )
            
            for line in process.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
            
            process.wait()
            
            elapsed = time.time() - start_time
            if process.returncode != 0:
                logger.error(f"Scraper returned exit code {process.returncode} after {elapsed:.2f}s")
            else:
                logger.info(f"✅ Batch completed in {elapsed:.2f}s")
            
            # Mark each query in the batch as completed (even on failure — we don't want to retry forever)
            for city, school_type in batch:
                tracker.mark_completed(current_state, city, school_type)
            
        except Exception as e:
            logger.error(f"Error running scraper: {e}")
            # Still mark as done to avoid infinite retry loops
            for city, school_type in batch:
                tracker.mark_completed(current_state, city, school_type)
        
        # 4. Save position
        tracker.advance_state(state_idx, cycle)
        
        if test_run:
            logger.info("Test run complete. Exiting.")
            break
        
        # 5. Anti-bot delay
        delay = random.randint(15, 45)
        logger.info(f"⏳ Anti-bot delay: {delay}s before next batch...")
        time.sleep(delay)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="State-by-State Lead Generator")
    parser.add_argument("--test", action="store_true", help="Run only one batch")
    parser.add_argument("--status", action="store_true", help="Print current progress and exit")
    args = parser.parse_args()
    
    if args.status:
        tracker = ScrapeProgressTracker()
        progress = tracker.get_state_progress()
        current = STATE_ORDER[progress["state_index"]]
        print(f"\n📍 Current State: {current} (Cycle {progress['cycle']})")
        print(f"{'='*50}")
        for state in STATE_ORDER:
            stats = tracker.get_state_stats(state)
            marker = "→" if state == current else " "
            pct = (stats['completed'] / stats['total'] * 100) if stats['total'] else 0
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            print(f" {marker} {state:20s} [{bar}] {pct:5.1f}% ({stats['completed']}/{stats['total']})")
    else:
        run_pipeline(test_run=args.test)
