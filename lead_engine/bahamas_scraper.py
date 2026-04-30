"""
Bahamas Retreat — Free Florida Executive Scraper.

Scrapes executives (CEO/Founder/COO/CMO/President/VP) at small-to-mid-size
businesses in Florida and nearby states (GA, AL, SC, NC) so we can pitch them
on hosting corporate retreats at our Bahamas villaplex.

Design constraints:
    * 100% FREE — no Apify, no Hunter, no Apollo. Uses Playwright (Chromium)
      against public Google Maps, plus the public Florida SunBiz registry,
      plus website crawling via lead_engine/website_crawler.py.
    * Reuses existing modules:
        - lead_engine/email_verifier.py       (DNS MX + catch-all)
        - lead_engine/website_crawler.py      (BeautifulSoup contact extraction)
        - lead_engine/contact_scorer.py       (title hierarchy)
        - lead_engine/db.py                   (SQLite storage)
        - lead_engine/niches.py "executives"  (preset registered)

Public surface:
    scrape_florida_executives(industries, cities, max_per_query=50, run_id=None,
                              db=None, verifier=None) -> dict
        Orchestrates Maps -> website crawl -> verify -> score -> DB insert.

    search_maps_free(niche, city, max_results, search_variations) -> list[dict]
        Drop-in replacement for lead_engine/scraper.py:search_maps that uses
        Playwright instead of Apify. harvest.py routes the "executives" niche
        through this function.

    sunbiz_lookup(company_name) -> dict | None
        Bonus: free Florida SunBiz public registry lookup. Returns
        {"company": ..., "officers": [...], "address": ...}. Optional, used
        opportunistically to enrich website crawl results when no executive
        names are found on the company website.

Playwright is imported lazily so the module imports cleanly even when
Playwright is not installed; in that case search_maps_free returns []
and a clear log line instructs the operator to `pip install playwright`.
"""
from __future__ import annotations

import logging
import os
import re
import sys
import time
from typing import Dict, List, Optional
from urllib.parse import quote_plus, urlparse

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lead_engine.contact_scorer import select_top_contacts
from lead_engine.db import HarvestDB
from lead_engine.email_verifier import EmailVerifier
from lead_engine.niches import get_niche_config
from lead_engine.website_crawler import extract_contacts

logger = logging.getLogger("lead_engine.bahamas")

# -----------------------------------------------------------------------------
# Defaults
# -----------------------------------------------------------------------------

# B2B verticals likely to host corporate retreats.
DEFAULT_INDUSTRIES: List[str] = [
    "law firms",
    "real estate companies",
    "marketing agencies",
    "software companies",
    "consulting firms",
    "investment firms",
    "financial advisors",
    "private equity firms",
    "wealth management firms",
    "accounting firms",
]

# Florida + nearby southeast states.
DEFAULT_CITIES: List[str] = [
    "Miami FL", "Fort Lauderdale FL", "West Palm Beach FL", "Boca Raton FL",
    "Tampa FL", "Orlando FL", "Jacksonville FL", "Naples FL", "Sarasota FL",
    "Atlanta GA", "Savannah GA",
    "Charlotte NC", "Raleigh NC",
    "Charleston SC", "Greenville SC",
    "Birmingham AL",
]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


# -----------------------------------------------------------------------------
# Playwright availability
# -----------------------------------------------------------------------------

def _have_playwright() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


# -----------------------------------------------------------------------------
# Google Maps via Playwright (free)
# -----------------------------------------------------------------------------

def search_maps_free(
    niche: str,
    city: str,
    max_results: int = 50,
    search_variations: Optional[List[str]] = None,
) -> List[Dict]:
    """
    Free Google Maps scraper using Playwright. Drop-in replacement for the
    Apify-backed lead_engine.scraper.search_maps signature.

    Returns a list of normalized business dicts:
        {name, niche, category, website, phone, address, city, state, raw_emails}
    """
    if not _have_playwright():
        logger.error(
            "Playwright not installed. Install with: "
            "`pip install playwright && playwright install chromium`. "
            "Skipping Maps scrape for %s.", city
        )
        return []

    from playwright.sync_api import sync_playwright

    # Build query terms. For "executives" niche the variations already end
    # with "in" so we just append the city.
    variations = search_variations or [niche]
    queries: List[str] = []
    for v in variations:
        v = v.strip()
        if v.endswith(" in") or v.endswith(" in "):
            queries.append(f"{v.strip()} {city}")
        elif " in " in v:
            queries.append(v)  # already a complete phrase
        else:
            queries.append(f"{v} in {city}")

    # Cap how many queries we run per city to stay under max_results overall.
    per_query_cap = max(5, max_results // max(1, len(queries)))
    state = _state_from_city(city)
    city_only = _city_from_city(city)

    businesses: List[Dict] = []
    seen_names: set = set()

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as e:
            logger.error("Failed to launch Chromium (run `playwright install chromium`): %s", e)
            return []

        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=USER_AGENT,
        )

        for query in queries:
            if len(businesses) >= max_results:
                break
            try:
                results = _scrape_query(context, query, per_query_cap)
            except Exception as e:
                logger.warning("Maps scrape failed for %r: %s", query, e)
                continue

            for r in results:
                key = r["name"].lower().strip()
                if not key or key in seen_names:
                    continue
                seen_names.add(key)
                r.setdefault("city", city_only)
                r.setdefault("state", state)
                r.setdefault("niche", niche)
                businesses.append(r)
                if len(businesses) >= max_results:
                    break

        try:
            browser.close()
        except Exception:
            pass

    logger.info("[%s] free Maps scrape: %d businesses across %d queries",
                city, len(businesses), len(queries))
    return businesses


def _scrape_query(context, query: str, max_results: int) -> List[Dict]:
    """Scrape one Google Maps query inside a Playwright browser context."""
    page = context.new_page()
    out: List[Dict] = []
    try:
        # Direct URL navigation bypasses the search input entirely.
        # This is far more robust than relying on `input#searchboxinput`.
        encoded_query = quote_plus(query)
        page.goto(
            f"https://www.google.com/maps/search/{encoded_query}",
            timeout=45000,
            wait_until="domcontentloaded",
        )

        # Consent banner — best-effort, multiple selectors.
        for label in ("Accept all", "I agree", "Reject all", "Aceitar tudo"):
            try:
                btn = page.get_by_role("button", name=label)
                if btn.count() > 0 and btn.first.is_visible(timeout=1000):
                    btn.first.click()
                    page.wait_for_timeout(1500)
                    break
            except Exception:
                pass

        # Wait for the results feed (or single-result detail panel).
        # Try multiple selectors with shorter individual timeouts.
        feed_loaded = False
        for sel in ['div[role="feed"]', 'div[aria-label*="Results"]', 'div[role="main"]']:
            try:
                page.wait_for_selector(sel, timeout=8000)
                feed_loaded = True
                break
            except Exception:
                continue

        if not feed_loaded:
            logger.debug("No results feed for %r — likely zero results", query)
            return out

        feed = page.locator('div[role="feed"]')
        if feed.count() == 0:
            return out

        # Scroll to load up to max_results cards.
        for _ in range(12):
            try:
                feed.evaluate("el => el.scrollTop = el.scrollHeight")
            except Exception:
                break
            page.wait_for_timeout(1400)
            count = feed.locator('div[role="article"]').count()
            if count >= max_results:
                break
            try:
                if page.get_by_text("You've reached the end of the list").is_visible():
                    break
            except Exception:
                pass

        cards = feed.locator('div[role="article"]')
        n = min(cards.count(), max_results)
        for i in range(n):
            try:
                card = cards.nth(i)
                name = card.get_attribute("aria-label") or ""
                name = name.replace("Visit ", "").strip()
                if not name:
                    continue

                # Website (preferred) or first non-google link.
                website = ""
                wb = card.locator('a[data-value="Website"]')
                if wb.count() > 0:
                    website = wb.first.get_attribute("href") or ""
                if not website:
                    for link in card.locator("a").all():
                        href = link.get_attribute("href") or ""
                        if href.startswith("http") and "google.com" not in href:
                            website = href
                            break

                text = card.text_content() or ""
                phone_match = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
                phone = phone_match.group(0) if phone_match else ""

                out.append({
                    "name": name,
                    "category": "",
                    "website": website,
                    "phone": phone,
                    "address": "",
                    "raw_emails": [],
                })
            except Exception as e:
                logger.debug("Card %d parse error: %s", i, e)
                continue
    finally:
        try:
            page.close()
        except Exception:
            pass

    return out


def _state_from_city(city: str) -> str:
    parts = city.strip().split()
    if len(parts) >= 2 and len(parts[-1]) == 2 and parts[-1].isupper():
        return parts[-1]
    return ""


def _city_from_city(city: str) -> str:
    parts = city.strip().split()
    if len(parts) >= 2 and len(parts[-1]) == 2 and parts[-1].isupper():
        return " ".join(parts[:-1])
    return city.strip()


# -----------------------------------------------------------------------------
# Florida SunBiz lookup (bonus, free public registry)
# -----------------------------------------------------------------------------

SUNBIZ_SEARCH_URL = "https://search.sunbiz.org/Inquiry/CorporationSearch/SearchResults"
SUNBIZ_BASE = "https://search.sunbiz.org"


def sunbiz_lookup(company_name: str, timeout: int = 12) -> Optional[Dict]:
    """
    Look up a Florida company in the public SunBiz registry. Returns:
        {"company": str, "address": str, "officers": [{"name": str, "title": str}, ...]}
    or None on failure. No API key, no auth required.
    """
    if not company_name:
        return None
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("beautifulsoup4 not available; skipping SunBiz lookup")
        return None

    params = {
        "inquiryType": "EntityName",
        "searchTerm": company_name,
        "searchNameOrder": company_name.upper(),
    }
    headers = {"User-Agent": USER_AGENT}

    try:
        resp = requests.get(SUNBIZ_SEARCH_URL, params=params, headers=headers,
                            timeout=timeout)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")

        # Take the first result link.
        link = soup.select_one("table a[href*='SearchResultDetail']")
        if not link:
            return None
        detail_url = SUNBIZ_BASE + link.get("href", "")
        if not detail_url.startswith("http"):
            return None

        detail_resp = requests.get(detail_url, headers=headers, timeout=timeout)
        if detail_resp.status_code != 200:
            return None
        detail = BeautifulSoup(detail_resp.text, "html.parser")

        # Officer / Director block — SunBiz renders these in a labelled section.
        officers: List[Dict[str, str]] = []
        for section in detail.find_all(["div", "section"]):
            heading = section.find(["h3", "h4", "strong"])
            if not heading:
                continue
            heading_text = heading.get_text(strip=True).lower()
            if "officer" in heading_text or "director" in heading_text:
                # Each officer block typically: title line then name line.
                lines = [l.strip() for l in section.get_text("\n").split("\n") if l.strip()]
                title = ""
                for line in lines:
                    upper = line.upper()
                    if upper.startswith("TITLE"):
                        title = line.split(None, 1)[-1].strip()
                    elif (re.match(r"^[A-Z][A-Z\-' ]+,\s*[A-Z]", line)
                          or re.match(r"^[A-Z][a-z]+\s+[A-Z][a-z]+", line)):
                        if line.lower() not in {"name & address", "title"}:
                            officers.append({"name": _titlecase_name(line), "title": title})
                            title = ""

        company_el = detail.find(string=re.compile(r"Detail by Entity Name", re.I))
        company = company_name
        if company_el:
            sib = company_el.find_next("p")
            if sib:
                company = sib.get_text(strip=True) or company

        address_el = detail.find(string=re.compile(r"Principal Address", re.I))
        address = ""
        if address_el:
            block = address_el.find_parent()
            if block:
                address = " ".join(
                    s.strip() for s in block.get_text("\n").split("\n")
                    if s.strip() and "Principal Address" not in s
                )

        return {"company": company, "address": address, "officers": officers}
    except Exception as e:
        logger.debug("SunBiz lookup failed for %r: %s", company_name, e)
        return None


def _titlecase_name(s: str) -> str:
    s = s.strip().rstrip(",")
    # Handle "LASTNAME, FIRSTNAME" -> "Firstname Lastname"
    if "," in s:
        last, first = [p.strip() for p in s.split(",", 1)]
        s = f"{first} {last}"
    return " ".join(p.capitalize() for p in s.split())


# -----------------------------------------------------------------------------
# Orchestrator
# -----------------------------------------------------------------------------

def scrape_florida_executives(
    industries: Optional[List[str]] = None,
    cities: Optional[List[str]] = None,
    max_per_query: int = 50,
    run_id: Optional[int] = None,
    db: Optional[HarvestDB] = None,
    verifier: Optional[EmailVerifier] = None,
    use_sunbiz: bool = False,
) -> Dict:
    """
    Orchestrate the full Florida-executives scrape: Maps -> website crawl ->
    verify -> score -> SQLite. Returns aggregate stats.
    """
    industries = industries or DEFAULT_INDUSTRIES
    cities = cities or DEFAULT_CITIES

    db = db or HarvestDB()
    verifier = verifier or EmailVerifier()
    if run_id is None:
        run_id = db.create_run("executives", ", ".join(cities))

    config = get_niche_config("executives")
    totals = {"businesses": 0, "contacts": 0, "verified": 0,
              "run_id": run_id, "cities": len(cities), "industries": len(industries)}

    for city in cities:
        logger.info("=== %s ===", city)
        for industry in industries:
            query = f"{industry} in"  # search_maps_free will append the city
            biz_list = search_maps_free(
                niche="executives",
                city=city,
                max_results=max_per_query,
                search_variations=[query],
            )
            for biz in biz_list:
                inserted = _process_business(biz, run_id, db, verifier,
                                             industry, use_sunbiz)
                totals["businesses"] += 1 if inserted["business"] else 0
                totals["contacts"] += inserted["contacts"]
                totals["verified"] += inserted["verified"]

    db.complete_run(run_id)
    logger.info("Bahamas scrape complete: %s", totals)
    return totals


def _process_business(
    biz: Dict, run_id: int, db: HarvestDB, verifier: EmailVerifier,
    industry: str, use_sunbiz: bool,
) -> Dict:
    """Crawl, verify, score and insert one business + its top contacts."""
    out = {"business": False, "contacts": 0, "verified": 0}
    biz["category"] = biz.get("category") or industry
    business_id = db.insert_business(run_id, biz)
    if not business_id:
        return out
    out["business"] = True

    contacts: List[Dict] = list(biz.get("raw_emails", []))

    website = biz.get("website") or ""
    if website:
        try:
            crawled = extract_contacts(website, "executives")
            for email in crawled.get("emails", []):
                if not any(c.get("email") == email for c in contacts):
                    contacts.append({"email": email, "title": ""})
            for c in crawled.get("contacts", []):
                if c.get("email") and not any(x.get("email") == c["email"] for x in contacts):
                    contacts.append(c)
        except Exception as e:
            logger.debug("Crawl failed for %s: %s", website, e)

    # Optional SunBiz enrichment for FL companies that look anonymous.
    if use_sunbiz and biz.get("state") == "FL" and not any(c.get("name") for c in contacts):
        sb = sunbiz_lookup(biz.get("name", ""))
        if sb and sb.get("officers"):
            domain = _domain_from_website(website)
            for officer in sb["officers"][:5]:
                name = officer.get("name", "")
                title = officer.get("title", "")
                inferred = ""
                if name and domain:
                    parts = name.split()
                    if len(parts) >= 2:
                        inferred = f"{parts[0].lower()}.{parts[-1].lower()}@{domain}"
                contacts.append({
                    "name": name, "title": title,
                    "email": inferred, "email_inferred": bool(inferred),
                })

    # DNS-only verification (no SMTP RCPT — we'd be blocked).
    for c in contacts:
        email = (c.get("email") or "").strip().lower()
        if not email:
            continue
        result = verifier.verify(email)
        c["email_status"] = result.status
        c["mx_host"] = result.mx_host
        c["is_catch_all"] = result.is_catch_all

    top = select_top_contacts(contacts, "executives", max_contacts=3)
    for c in top:
        name = c.get("name", "") or ""
        first, last = "", ""
        if name:
            parts = name.split()
            first = parts[0]
            last = parts[-1] if len(parts) > 1 else ""
        cid = db.insert_contact(business_id, {
            "email": c.get("email", ""),
            "first_name": first,
            "last_name": last,
            "title": c.get("title", ""),
            "seniority_score": c.get("seniority_score", 0),
            "email_status": c.get("email_status", "unknown"),
            "mx_host": c.get("mx_host", ""),
            "is_catch_all": c.get("is_catch_all", False),
        })
        if cid:
            out["contacts"] += 1
            if c.get("email_status") == "verified":
                out["verified"] += 1
    return out


def _domain_from_website(url: str) -> str:
    if not url:
        return ""
    try:
        host = urlparse(url if url.startswith("http") else "http://" + url).netloc
        return host.lower().lstrip("www.")
    except Exception:
        return ""


# -----------------------------------------------------------------------------
# CLI shim — lets you invoke the scraper directly during testing.
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ap = argparse.ArgumentParser(description="Bahamas Retreat free Florida executive scraper")
    ap.add_argument("--cities", type=str, default="Miami FL,Tampa FL")
    ap.add_argument("--industries", type=str, default=",".join(DEFAULT_INDUSTRIES[:3]))
    ap.add_argument("--max-per-query", type=int, default=20)
    ap.add_argument("--sunbiz", action="store_true", help="Enrich FL results with SunBiz officers")
    args = ap.parse_args()

    cities = [c.strip() for c in args.cities.split(",") if c.strip()]
    industries = [i.strip() for i in args.industries.split(",") if i.strip()]

    stats = scrape_florida_executives(
        industries=industries,
        cities=cities,
        max_per_query=args.max_per_query,
        use_sunbiz=args.sunbiz,
    )
    print(stats)
