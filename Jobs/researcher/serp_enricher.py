"""
Data Enrichment Module (Custom Scraper Version)

This module handles lead enrichment using data already present in the lead 
dictionary from the custom/Apify scraper. Legacy Serper/Outscraper logic 
has been removed.
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)

def enrich_lead(lead: Dict, campaign_type: str) -> Dict:
    """
    Main enrichment function that routes to campaign-specific enrichment.
    In the current custom scraper workflow, this is primarily a pass-through
    as the scraper already provides website context and social profiles.
    
    Args:
        lead: Lead data dictionary
        campaign_type: One of 'school', 'real_estate', 'pac'
    
    Returns:
        Enriched lead data
    """
    # Simply ensure the title is used as a fallback for school_name if not present
    if campaign_type == "school":
        if "school_name" not in lead:
            lead["school_name"] = lead.get("title", "")
            
    return lead
