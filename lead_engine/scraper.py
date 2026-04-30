"""
Apify Google Maps scraper integration.
Searches Google Maps for businesses matching a niche + city and returns normalized results.
"""
import os
import logging
import time
from typing import List, Dict, Optional

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("lead_engine.scraper")


def search_maps(niche: str, city: str, max_results: int = 100,
                search_variations: Optional[List[str]] = None) -> List[Dict]:
    """
    Search Google Maps via Apify for businesses matching niche in city.
    Returns normalized business dicts.
    """
    token = os.getenv("APIFY_API_TOKEN")
    if not token:
        logger.error("APIFY_API_TOKEN not set in environment")
        return []

    try:
        from apify_client import ApifyClient
    except ImportError:
        logger.error("apify-client not installed. Run: pip install apify-client")
        return []

    client = ApifyClient(token)

    # Build search terms
    if search_variations:
        terms = [f"{v} in {city}" for v in search_variations]
    else:
        terms = [f"{niche} in {city}"]

    run_input = {
        "searchStringsArray": terms,
        "maxCrawledPlacesPerSearch": max_results,
        "language": "en",
        "scrapeSocialMediaProfiles": False,
        "emailAndContactScrapingMode": "emailsFromWebsite",
        "onlyConfirmedEmails": True,
        "maxImages": 0,
        "maxReviews": 0,
    }

    logger.info(f"Searching Maps: {len(terms)} terms for {city} ({niche})")

    try:
        run = client.actor("compass/crawler-google-places").call(run_input=run_input)
        items = client.dataset(run["defaultDatasetId"]).list_items().items
        logger.info(f"Found {len(items)} results for {city}")
    except Exception as e:
        logger.error(f"Apify error for {city}: {e}")
        # Retry once after 5 seconds
        try:
            time.sleep(5)
            run = client.actor("compass/crawler-google-places").call(run_input=run_input)
            items = client.dataset(run["defaultDatasetId"]).list_items().items
            logger.info(f"Retry succeeded: {len(items)} results for {city}")
        except Exception as e2:
            logger.error(f"Apify retry failed for {city}: {e2}")
            return []

    # Normalize results
    businesses = []
    seen_names = set()

    for item in items:
        name = (item.get("title") or "").strip()
        if not name or name.lower() in seen_names:
            continue
        seen_names.add(name.lower())

        # Parse city/state from address
        address = item.get("address") or item.get("street") or ""
        item_city = item.get("city") or ""
        item_state = item.get("state") or ""

        if not item_city and address:
            parts = address.split(",")
            if len(parts) >= 2:
                item_city = parts[-2].strip()

        # Collect raw emails from Apify result
        raw_emails = []
        if item.get("emails"):
            for e in item["emails"]:
                if isinstance(e, dict):
                    raw_emails.append({"email": e.get("value", ""), "title": e.get("description", "")})
                elif isinstance(e, str):
                    raw_emails.append({"email": e, "title": ""})
        elif item.get("email"):
            raw_emails.append({"email": item["email"], "title": ""})

        businesses.append({
            "name": name,
            "niche": niche,
            "category": item.get("categoryName", ""),
            "website": item.get("website") or item.get("url") or "",
            "phone": item.get("phone") or item.get("phoneNumber") or "",
            "address": address,
            "city": item_city or city.split(",")[0].split(" ")[0] if "," in city else city,
            "state": item_state or (city.split()[-1] if len(city.split()) > 1 else ""),
            "raw_emails": raw_emails,
        })

    return businesses
