"""
Apollo-fed Bahamas Lead Scraper — high-throughput, BEC-free.

Strategy: Apollo's free tier won't give us named exec emails directly,
but it WILL give us ~164,000 high-fit US companies matching our ICP
(consulting, marketing, SaaS, design, professional services, 30-150 emp).

Pipeline:
  1. Apollo organizations/search  → company batch
  2. Per company, scrape website  → extract emails + named contacts
  3. DNS-verify emails (no BEC)   → drop ones with no MX record
  4. Push to Bahamas tab          → sender picks them up

Runs forever, paginates through Apollo until exhausted, then loops
with broader ICP filters to discover more companies.

Usage:
    python apollo_daemon.py \
        [--workers 10] [--per-page 100] [--max-pages 25]
        [--sheet-name "Bahamas Retreat - Leads"]
"""
from __future__ import annotations
import argparse
import logging
import os
import signal
import sys
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests
import urllib3

# Suppress InsecureRequestWarning — scraping small business sites with
# misconfigured certs is unavoidable, and the warnings drown out everything
# else in the Railway log buffer (500-line tail).
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from lead_engine.website_crawler import extract_contacts
from lead_engine.email_verifier import EmailVerifier
from sheets_integration import GoogleSheetsClient


# ============================================================================
# Configuration
# ============================================================================
APOLLO_API_KEY = os.environ.get("APOLLO_API_KEY", "ljD1V-8Qr90XximLPSVwqA")
APOLLO_BASE = "https://api.apollo.io/api/v1"

# ICP filters for Bahamas retreat buyers. Wider net 2026-05-15 — original
# 8 ICPs were exhausted (returning all dupes). Added 20+ more industries
# + slightly relaxed employee range (20-300 instead of 30-150) + added
# Canada to broaden the pool. Each variant unlocks ~5K-25K unique
# companies from Apollo's database.
EMP_RANGE = ["20,300"]
LOC_US_CA = ["United States", "Canada"]

ICP_VARIANTS = [
    # Original 8 (kept for resync of recent additions to those industries)
    {"name": "marketing-agency", "q_organization_keyword_tags": ["marketing agency", "advertising agency", "digital agency"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "consulting", "q_organization_keyword_tags": ["consulting", "management consulting", "strategy consulting"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "saas-tech", "q_organization_keyword_tags": ["saas", "software", "technology"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "design-agency", "q_organization_keyword_tags": ["design agency", "branding agency", "creative agency"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "executive-coaching", "q_organization_keyword_tags": ["executive coaching", "professional training", "leadership development"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "finance-services", "q_organization_keyword_tags": ["financial services", "wealth management", "venture capital", "private equity"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "biotech-pharma", "q_organization_keyword_tags": ["biotech", "pharmaceutical", "medical devices"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "real-estate-dev", "q_organization_keyword_tags": ["real estate", "property management", "real estate development"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},

    # 20 new variants — industries that actually book corporate retreats
    {"name": "healthcare-admin", "q_organization_keyword_tags": ["hospital", "healthcare administration", "medical group", "health system"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "events-hospitality", "q_organization_keyword_tags": ["event management", "event planning", "destination management", "corporate events"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "law-firms", "q_organization_keyword_tags": ["law firm", "legal services", "attorney"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "accounting-cpa", "q_organization_keyword_tags": ["accounting firm", "cpa firm", "tax advisory", "audit"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "architecture-engineering", "q_organization_keyword_tags": ["architecture firm", "engineering firm", "civil engineering"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "construction-gc", "q_organization_keyword_tags": ["general contractor", "construction", "commercial construction"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "insurance", "q_organization_keyword_tags": ["insurance brokerage", "insurance services", "underwriting"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "media-publishing", "q_organization_keyword_tags": ["media", "publishing", "broadcasting", "digital media"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "education-edtech", "q_organization_keyword_tags": ["edtech", "online learning", "private school", "training company"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "ecommerce-brands", "q_organization_keyword_tags": ["ecommerce", "direct to consumer", "online retail"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "manufacturing-hq", "q_organization_keyword_tags": ["manufacturing", "industrial manufacturing", "specialty manufacturing"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "transportation-logistics", "q_organization_keyword_tags": ["logistics", "supply chain", "freight", "transportation"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "food-beverage", "q_organization_keyword_tags": ["food and beverage", "restaurant group", "specialty food", "beverage company"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "fitness-wellness", "q_organization_keyword_tags": ["fitness", "wellness", "gym chain", "health and wellness"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "nonprofit-leadership", "q_organization_keyword_tags": ["nonprofit", "foundation", "philanthropy", "ngo"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "venture-capital-pe", "q_organization_keyword_tags": ["venture capital", "private equity", "investment firm"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "energy-cleantech", "q_organization_keyword_tags": ["clean energy", "renewable energy", "solar", "energy services"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "telecom-isp", "q_organization_keyword_tags": ["telecommunications", "internet service provider", "telecom services"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "automotive-dealer", "q_organization_keyword_tags": ["automotive dealer", "car dealership", "auto group"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "agriculture-ag", "q_organization_keyword_tags": ["agriculture", "agribusiness", "food production"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "gaming-esports", "q_organization_keyword_tags": ["gaming studio", "video games", "esports"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
    {"name": "crypto-web3", "q_organization_keyword_tags": ["cryptocurrency", "blockchain", "web3", "defi"], "organization_num_employees_ranges": EMP_RANGE, "organization_locations": LOC_US_CA},
]

DEFAULT_WORKERS = 10
DEFAULT_PER_PAGE = 100
DEFAULT_MAX_PAGES_PER_ICP = 25  # Apollo free typically caps at 25 pages
SHEET_NAME = "Ivy Bound - Campaign Leads"
SHEET_TAB = "Bahamas Retreat - Leads"

# ============================================================================
# Logging + signal handling
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("apollo_daemon")

_shutdown = False
def _handle_sigterm(signum, frame):
    global _shutdown
    _shutdown = True
    logger.info(f"Signal {signum} received — finishing current batch then exiting")

signal.signal(signal.SIGTERM, _handle_sigterm)
signal.signal(signal.SIGINT, _handle_sigterm)


# ============================================================================
# Apollo client
# ============================================================================
def apollo_search(icp_variant: dict, page: int, per_page: int) -> list:
    """Call Apollo organizations/search. Returns list of company dicts."""
    body = dict(icp_variant)
    body.pop("name", None)
    body["page"] = page
    body["per_page"] = per_page

    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "X-Api-Key": APOLLO_API_KEY,
    }
    try:
        r = requests.post(f"{APOLLO_BASE}/organizations/search",
                          headers=headers, json=body, timeout=30)
        if r.status_code != 200:
            logger.warning(f"Apollo HTTP {r.status_code} for ICP {icp_variant.get('name')} page {page}: {r.text[:200]}")
            return []
        return r.json().get("organizations", [])
    except Exception as e:
        logger.error(f"Apollo search failed for ICP {icp_variant.get('name')} page {page}: {e}")
        return []


# ============================================================================
# Per-company processing
# ============================================================================
def process_company(company: dict, verifier: EmailVerifier) -> list:
    """Scrape company website, verify emails via DNS only.
    Returns a list of lead dicts ready for the Bahamas tab."""
    name = company.get("name", "").strip()
    website = company.get("website_url") or company.get("primary_domain", "")
    if not website:
        return []

    if not website.startswith("http"):
        website = "https://" + website

    # Scrape website for emails + named contacts
    try:
        crawled = extract_contacts(website, "executives")
    except Exception as e:
        logger.debug(f"scrape failed for {website}: {e}")
        return []

    emails = list(crawled.get("emails", []))
    contacts = crawled.get("contacts", [])
    if not emails:
        # No emails on site? Try synthetic candidates (info@, contact@)
        try:
            host = urlparse(website).netloc.lower()
            if host.startswith("www."):
                host = host[4:]
            if host and "." in host:
                emails = [f"{p}@{host}" for p in ("info", "contact", "hello", "team")]
        except Exception:
            pass

    leads = []
    for email in emails[:5]:  # cap per company
        try:
            result = verifier.verify(email)
        except Exception as e:
            logger.debug(f"verify failed for {email}: {e}")
            continue
        if result.status not in ("verified", "catch_all"):
            continue

        # Match name from contacts if email pattern aligns (e.g. j.smith@... → John Smith)
        first_name, last_name, title = "", "", ""
        local = email.split("@")[0].lower()
        for c in contacts:
            nm = (c.get("name") or "").lower().split()
            if not nm: continue
            initials_or_first = nm[0]
            if initials_or_first.startswith(local[:1]) or initials_or_first in local:
                parts = c["name"].split()
                first_name = parts[0]
                last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
                title = c.get("title", "")
                break

        leads.append({
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "role": title,
            "school_name": name,
            "domain": website,
            "state": "",
            "city": "",
            "phone": (company.get("primary_phone", {}) or {}).get("number", "") if isinstance(company.get("primary_phone"), dict) else "",
            "status": "pending",
            "notes": f"Apollo+DNS | verified={result.status} | mx={result.mx_host}",
            "school_type": (company.get("industry") or "")[:50],
            "custom_data": "",
        })
    return leads


# ============================================================================
# Sheet sync
# ============================================================================
def append_to_sheet(leads: list, sheets_client, existing_emails: set) -> int:
    """Append new leads to the Bahamas tab, deduping by email."""
    if not leads:
        return 0
    ws = sheets_client.input_sheet.worksheet(SHEET_TAB)
    headers = ws.row_values(1)
    rows_to_append = []
    for lead in leads:
        e = lead["email"].lower().strip()
        if e in existing_emails:
            continue
        existing_emails.add(e)
        rows_to_append.append([lead.get(h, "") for h in headers])
    if rows_to_append:
        ws.append_rows(rows_to_append, value_input_option="RAW")
    return len(rows_to_append)


# ============================================================================
# Daemon main loop
# ============================================================================
def run_daemon(args):
    logger.info("=" * 70)
    logger.info("APOLLO DAEMON STARTED")
    logger.info(f"  ICP variants: {len(ICP_VARIANTS)}")
    logger.info(f"  Workers: {args.workers}")
    logger.info(f"  Per page: {args.per_page} | Max pages per ICP: {args.max_pages}")
    logger.info("=" * 70)

    verifier = EmailVerifier()
    sheets = GoogleSheetsClient(input_sheet_name=SHEET_NAME)
    sheets._authenticate()
    sheets.setup_sheets()

    # Bootstrap dedup set from existing sheet
    ws = sheets.input_sheet.worksheet(SHEET_TAB)
    existing = set()
    for r in ws.get_all_values()[1:]:
        if r and r[0]:
            existing.add(r[0].lower().strip())
    logger.info(f"Bootstrap: {len(existing)} existing emails in sheet")

    cycle = 0
    while not _shutdown:
        cycle += 1
        cycle_added = 0
        for icp in ICP_VARIANTS:
            if _shutdown: break
            logger.info(f"\n--- ICP {icp['name']} ---")
            for page in range(1, args.max_pages + 1):
                if _shutdown: break
                companies = apollo_search(icp, page, args.per_page)
                if not companies:
                    logger.info(f"  page {page}: 0 companies, moving to next ICP")
                    break

                # Process companies in parallel
                with ThreadPoolExecutor(max_workers=args.workers) as ex:
                    futures = {ex.submit(process_company, c, verifier): c for c in companies}
                    page_leads = []
                    for fut in as_completed(futures):
                        try:
                            leads = fut.result()
                        except Exception as e:
                            logger.debug(f"worker failed: {e}")
                            leads = []
                        page_leads.extend(leads)

                # Append to sheet
                appended = append_to_sheet(page_leads, sheets, existing)
                cycle_added += appended
                logger.info(f"  page {page}: {len(companies)} companies → {len(page_leads)} emails → {appended} new (dedup'd)")
                time.sleep(2)  # polite pacing

            # Polite delay between ICPs
            if not _shutdown:
                time.sleep(10)

        logger.info(f"\n=== Cycle #{cycle} complete | +{cycle_added} new verified leads ===")
        # After a full sweep, sleep before doing it again (new companies may appear in Apollo)
        if not _shutdown:
            sleep_for = 60 * 60 * 4  # 4 hours between full sweeps
            logger.info(f"Resting {sleep_for // 60} min before next full sweep")
            time.sleep(sleep_for)

    logger.info("Daemon stopped.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--per-page", type=int, default=DEFAULT_PER_PAGE)
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES_PER_ICP)
    args = parser.parse_args()
    run_daemon(args)


if __name__ == "__main__":
    main()
