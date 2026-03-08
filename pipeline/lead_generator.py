import os
import sys
import time
import random
import logging
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from sheets_integration import GoogleSheetsClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - LEAD_GEN - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('lead_generator.log')
    ]
)
logger = logging.getLogger(__name__)

# Very large list of Texas cities to scrape for private schools
TEXAS_CITIES = [
    "Houston", "San Antonio", "Dallas", "Austin", "Fort Worth", "El Paso", 
    "Arlington", "Corpus Christi", "Plano", "Lubbock", "Irving", "Laredo",
    "Garland", "Frisco", "McKinney", "Amarillo", "Grand Prairie", "Brownsville",
    "Killeen", "Pasadena", "Midland", "McAllen", "Denton", "Carrollton",
    "Round Rock", "Waco", "Abilene", "Pearland", "Odessa", "College Station",
    "Richardson", "Beaumont", "League City", "The Woodlands", "Tyler",
    "Sugar Land", "Allen", "Wichita Falls", "Conroe", "San Angelo",
    "New Braunfels", "Galveston", "Victoria", "Temple", "San Marcos",
    "Georgetown", "Mansfield", "Cedar Park", "Rowlett", "Pflugerville",
    "Euless", "DeSoto", "Grapevine", "Bedford", "Galveston"
]

MAX_LEAD_LIMIT = 50000
SHEET_NAME = "Ivy Bound - Scraped Leads"
PIPELINE_DIR = Path(__file__).resolve().parent
SCRAPER_SCRIPT = PIPELINE_DIR / "google_maps_scraper.py"

def get_current_lead_count() -> int:
    try:
        client = GoogleSheetsClient(input_sheet_name=SHEET_NAME)
        client.setup_sheets()
        records = client._fetch_all_records()
        return len(records)
    except Exception as e:
        logger.error(f"Failed to check sheet count: {e}")
        # If we can't check, assume it's safe to run one iteration or fail safely
        return 0

def run_pipeline(test_run: bool = False):
    logger.info("Starting Continuous Lead Generation Pipeline...")
    
    # Randomize city order so restarting doesn't just hit the same first 5 forever
    random.shuffle(TEXAS_CITIES)
    
    SCHOOL_TYPES = [
        "Private high schools",
        "Public high schools",
        "Middle schools"
    ]
    
    city_idx = 0
    type_idx = 0
    
    while True:
        # 1. State check
        current_leads = get_current_lead_count()
        logger.info(f"Current lead count in sheet: {current_leads} / {MAX_LEAD_LIMIT}")
        
        if current_leads >= MAX_LEAD_LIMIT:
            logger.warning(f"Lead limit reached ({MAX_LEAD_LIMIT}). Pausing generator for 6 hours.")
            time.sleep(60 * 60 * 6) # Sleep for 6 hours
            continue
            
        # 2. Prepare query
        city = TEXAS_CITIES[city_idx % len(TEXAS_CITIES)]
        school_type = SCHOOL_TYPES[type_idx % len(SCHOOL_TYPES)]
        
        query = f"{school_type} in {city}, TX"
        
        # Advance counters: rotate school types first, then cities
        type_idx += 1
        if type_idx % len(SCHOOL_TYPES) == 0:
            city_idx += 1
            
        logger.info(f"Starting Scraper subprocess for query: '{query}'")
        
        # 3. Run scraper
        try:
            # We run via subprocess to isolate memory and playwright event loops
            cmd = [
                sys.executable, str(SCRAPER_SCRIPT),
                "--queries", query,
                "--sheet-name", SHEET_NAME
            ]
            
            # Using Popen to stream output
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(PIPELINE_DIR)
            )
            
            for line in process.stdout:
                print(f"[SCRAPER] {line.strip()}")
                
            process.wait()
            
            if process.returncode != 0:
                logger.error(f"Scraper returned non-zero exit code: {process.returncode}")
                
        except Exception as e:
            logger.error(f"Error running scraper subprocess: {e}")
            
        # 4. Anti-Bot Delay
        if test_run:
            logger.info("Test run complete. Exiting.")
            break
            
        # Wait 30 to 90 seconds between queries to avoid Google Maps IP bans
        delay_seconds = random.randint(30, 90)
        logger.info(f"Subprocess finished. Anti-Bot delay: sleeping for {delay_seconds} seconds before next query...")
        time.sleep(delay_seconds)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Continuous Lead Generator")
    parser.add_argument("--test", action="store_true", help="Run only one iteration for testing")
    args = parser.parse_args()
    
    run_pipeline(test_run=args.test)
