"""
Niche-configurable contact scoring and ranking.
Scores contacts by decision-maker seniority and filters generic addresses.
"""
from typing import List, Dict
from lead_engine.niches import get_niche_config, GENERIC_EMAIL_PREFIXES


def score_contact(email: str, title: str, niche: str) -> int:
    """Score a contact by seniority. Higher = more senior. -1 = disqualified."""
    if not email or "@" not in email:
        return -1
    if email.startswith("http"):
        return -1

    prefix = email.split("@")[0].lower().strip()
    if prefix in GENERIC_EMAIL_PREFIXES:
        return -1

    config = get_niche_config(niche)
    title_lower = (title or "").lower()

    for tier_idx, keywords in enumerate(config.title_hierarchy):
        if any(kw in title_lower for kw in keywords):
            return len(config.title_hierarchy) - tier_idx

    return 0  # Unknown title — still better than generic


def select_top_contacts(contacts: List[Dict], niche: str, max_contacts: int = 3) -> List[Dict]:
    """Score, rank, and return top N contacts for a business."""
    scored = []
    seen_emails = set()

    for contact in contacts:
        email = (contact.get("email") or "").strip().lower()
        title = contact.get("title", "")
        if not email or email in seen_emails:
            continue
        s = score_contact(email, title, niche)
        if s >= 0:
            contact["seniority_score"] = s
            scored.append(contact)
            seen_emails.add(email)

    scored.sort(key=lambda x: x.get("seniority_score", 0), reverse=True)
    return scored[:max_contacts]
