"""
Niche presets for the universal lead generation engine.
Configures search terms, title hierarchies, subpage paths, and filters per niche.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class NicheConfig:
    search_variations: List[str]
    title_hierarchy: List[List[str]]
    subpage_paths: List[str]
    institution_guard: List[str] = field(default_factory=list)


NICHE_PRESETS: Dict[str, NicheConfig] = {
    "schools": NicheConfig(
        search_variations=[
            "private school", "public school", "charter school",
            "academy", "preparatory school", "high school",
            "middle school", "K-12 school", "religious school",
            "catholic school", "christian school",
        ],
        title_hierarchy=[
            ["superintendent", "executive director", "ceo", "president", "founder", "owner"],
            ["principal", "head of school", "headmaster", "headmistress"],
            ["director of admissions", "director of education", "director of curriculum", "director"],
            ["academic dean", "dean of students", "dean"],
            ["college counselor", "guidance counselor", "college advisor", "counselor", "advisor"],
            ["admissions", "enrollment", "registrar"],
        ],
        subpage_paths=["/about", "/contact", "/staff", "/admissions", "/our-team", "/faculty"],
        institution_guard=["university", "college", "preschool", "daycare", "nursery"],
    ),
    "private schools": NicheConfig(
        search_variations=[
            "private school", "independent school", "academy",
            "preparatory school", "christian school", "catholic school",
            "montessori school", "parochial school",
        ],
        title_hierarchy=[
            ["superintendent", "executive director", "ceo", "president", "founder", "owner"],
            ["principal", "head of school", "headmaster", "headmistress"],
            ["director of admissions", "director of education", "director"],
            ["academic dean", "dean of students", "dean"],
            ["college counselor", "guidance counselor", "counselor", "advisor"],
            ["admissions", "enrollment"],
        ],
        subpage_paths=["/about", "/contact", "/staff", "/admissions", "/our-team", "/faculty"],
        institution_guard=["university", "college", "preschool", "daycare", "nursery"],
    ),
    "dentists": NicheConfig(
        search_variations=[
            "dentist", "dental office", "dental clinic",
            "orthodontist", "oral surgeon", "pediatric dentist",
            "cosmetic dentist", "family dentist",
        ],
        title_hierarchy=[
            ["owner", "founder", "managing partner", "practice owner"],
            ["dds", "dmd", "lead dentist", "chief dental officer"],
            ["associate dentist", "dentist", "orthodontist"],
            ["office manager", "practice manager", "operations manager"],
            ["dental hygienist", "hygienist"],
            ["front desk", "receptionist", "scheduling"],
        ],
        subpage_paths=["/about", "/contact", "/meet-the-team", "/our-doctors", "/staff", "/team"],
        institution_guard=["dental school", "university", "college"],
    ),
    "lawyers": NicheConfig(
        search_variations=[
            "law firm", "attorney", "lawyer", "legal office",
            "personal injury lawyer", "family law attorney",
            "criminal defense attorney", "estate planning attorney",
        ],
        title_hierarchy=[
            ["managing partner", "founding partner", "named partner", "owner"],
            ["senior partner", "partner", "shareholder"],
            ["of counsel", "senior associate", "senior attorney"],
            ["associate attorney", "associate", "attorney"],
            ["paralegal", "legal assistant"],
            ["office manager", "legal secretary"],
        ],
        subpage_paths=["/about", "/contact", "/attorneys", "/our-team", "/lawyers", "/staff"],
        institution_guard=["law school", "bar association", "legal aid"],
    ),
    "accountants": NicheConfig(
        search_variations=[
            "accounting firm", "CPA", "accountant", "CPA firm",
            "tax preparer", "bookkeeper", "financial advisor",
        ],
        title_hierarchy=[
            ["managing partner", "founding partner", "owner", "principal"],
            ["senior partner", "partner", "cpa", "director"],
            ["senior accountant", "senior associate", "tax manager"],
            ["staff accountant", "associate", "tax preparer"],
            ["bookkeeper", "accounting clerk"],
            ["office manager", "administrative assistant"],
        ],
        subpage_paths=["/about", "/contact", "/our-team", "/staff", "/professionals"],
        institution_guard=["university", "college"],
    ),
    "realtors": NicheConfig(
        search_variations=[
            "real estate agent", "realtor", "real estate office",
            "real estate broker", "property management",
        ],
        title_hierarchy=[
            ["broker", "managing broker", "owner", "principal broker"],
            ["team leader", "senior agent", "associate broker"],
            ["real estate agent", "realtor", "agent"],
            ["transaction coordinator", "office manager"],
        ],
        subpage_paths=["/about", "/contact", "/agents", "/our-team", "/meet-us"],
        institution_guard=[],
    ),
    "executives": NicheConfig(
        search_variations=[
            "companies in",
            "businesses in",
            "law firms in",
            "real estate companies in",
            "marketing agencies in",
            "software companies in",
            "consulting firms in",
            "investment firms in",
            "financial advisors in",
        ],
        title_hierarchy=[
            ["ceo", "founder", "owner", "president", "managing partner"],
            ["coo", "cfo", "cmo", "cto", "executive vice president"],
            ["vp", "vice president", "director"],
            ["manager"],
        ],
        subpage_paths=["/about", "/team", "/leadership", "/our-team", "/about-us", "/our-people"],
        institution_guard=[],
    ),
    "chiropractors": NicheConfig(
        search_variations=[
            "chiropractor", "chiropractic office", "chiropractic clinic",
            "sports chiropractor", "family chiropractor",
        ],
        title_hierarchy=[
            ["owner", "founder", "managing partner"],
            ["dc", "chiropractor", "lead chiropractor"],
            ["associate chiropractor", "associate"],
            ["office manager", "practice manager"],
            ["massage therapist", "physical therapist"],
        ],
        subpage_paths=["/about", "/contact", "/meet-the-team", "/our-doctors", "/staff"],
        institution_guard=["chiropractic school", "university"],
    ),
}


def get_niche_config(niche: str) -> NicheConfig:
    """Get config for a niche. Falls back to a generic config for unknown niches."""
    key = niche.lower().strip()
    if key in NICHE_PRESETS:
        return NICHE_PRESETS[key]

    # Check partial matches
    for preset_key, config in NICHE_PRESETS.items():
        if key in preset_key or preset_key in key:
            return config

    # Generic fallback
    return NicheConfig(
        search_variations=[niche],
        title_hierarchy=[
            ["owner", "founder", "ceo", "president", "managing partner"],
            ["director", "manager", "partner", "vp"],
            ["supervisor", "lead", "senior"],
            ["associate", "specialist", "coordinator"],
        ],
        subpage_paths=["/about", "/contact", "/our-team", "/staff"],
        institution_guard=[],
    )


# Generic email prefixes to skip (not decision-makers)
GENERIC_EMAIL_PREFIXES = {
    "info", "admin", "office", "contact", "hello", "help", "support",
    "reception", "secretary", "webmaster", "noreply", "no-reply",
    "mail", "general", "inquiries", "inquiry", "registrar", "accounts",
    "billing", "sales", "marketing", "hr", "jobs", "careers",
    "feedback", "press", "media", "newsletter", "subscribe",
}

# Disposable email domains (common ones)
DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "tempmail.com", "throwaway.email",
    "yopmail.com", "sharklasers.com", "guerrillamailblock.com", "grr.la",
    "dispostable.com", "mailnesia.com", "maildrop.cc", "discard.email",
    "trashmail.com", "trashmail.me", "trashmail.net", "mailcatch.com",
    "temp-mail.org", "tempail.com", "tempr.email", "10minutemail.com",
    "minutemail.com", "emailondeck.com", "mohmal.com", "burnermail.io",
    "mailsac.com", "harakirimail.com", "spamgourmet.com", "mytrashmail.com",
    "getnada.com", "tempinbox.com", "fakeinbox.com", "mailnator.com",
    "binkmail.com", "safetymail.info", "filzmail.com", "trashymail.com",
    "mailexpire.com", "tempmailer.com", "trash-mail.com", "jetable.org",
    "guerrillamail.info", "guerrillamail.de", "guerrillamail.net",
    "guerrillamail.biz", "spam4.me", "getairmail.com", "mailforspam.com",
    "tempomail.fr", "mailtemp.info", "tmpmail.net", "tmpmail.org",
}

# US cities by state (top cities for --states expansion)
US_STATE_CITIES: Dict[str, List[str]] = {
    "AL": ["Birmingham", "Montgomery", "Huntsville", "Mobile", "Tuscaloosa"],
    "AK": ["Anchorage", "Fairbanks", "Juneau"],
    "AZ": ["Phoenix", "Tucson", "Mesa", "Scottsdale", "Chandler", "Tempe"],
    "AR": ["Little Rock", "Fort Smith", "Fayetteville", "Springdale"],
    "CA": ["Los Angeles", "San Francisco", "San Diego", "San Jose", "Sacramento", "Oakland", "Fresno", "Long Beach", "Irvine", "Pasadena"],
    "CO": ["Denver", "Colorado Springs", "Aurora", "Fort Collins", "Boulder"],
    "CT": ["Hartford", "New Haven", "Stamford", "Bridgeport", "Waterbury"],
    "DE": ["Wilmington", "Dover", "Newark"],
    "FL": ["Miami", "Orlando", "Tampa", "Jacksonville", "Fort Lauderdale", "St. Petersburg", "Sarasota", "Naples", "Tallahassee", "Boca Raton"],
    "GA": ["Atlanta", "Savannah", "Augusta", "Columbus", "Athens"],
    "HI": ["Honolulu", "Hilo", "Kailua"],
    "ID": ["Boise", "Meridian", "Nampa", "Idaho Falls"],
    "IL": ["Chicago", "Aurora", "Naperville", "Springfield", "Rockford"],
    "IN": ["Indianapolis", "Fort Wayne", "Evansville", "South Bend", "Carmel"],
    "IA": ["Des Moines", "Cedar Rapids", "Davenport", "Iowa City"],
    "KS": ["Wichita", "Overland Park", "Kansas City", "Topeka"],
    "KY": ["Louisville", "Lexington", "Bowling Green", "Covington"],
    "LA": ["New Orleans", "Baton Rouge", "Shreveport", "Lafayette"],
    "ME": ["Portland", "Lewiston", "Bangor"],
    "MD": ["Baltimore", "Bethesda", "Rockville", "Annapolis", "Silver Spring"],
    "MA": ["Boston", "Worcester", "Springfield", "Cambridge", "Newton"],
    "MI": ["Detroit", "Grand Rapids", "Ann Arbor", "Lansing", "Kalamazoo"],
    "MN": ["Minneapolis", "St. Paul", "Rochester", "Duluth", "Bloomington"],
    "MS": ["Jackson", "Gulfport", "Hattiesburg", "Biloxi"],
    "MO": ["Kansas City", "St. Louis", "Springfield", "Columbia"],
    "MT": ["Billings", "Missoula", "Great Falls", "Bozeman"],
    "NE": ["Omaha", "Lincoln", "Bellevue"],
    "NV": ["Las Vegas", "Reno", "Henderson", "North Las Vegas"],
    "NH": ["Manchester", "Nashua", "Concord"],
    "NJ": ["Newark", "Jersey City", "Trenton", "Princeton", "Edison"],
    "NM": ["Albuquerque", "Santa Fe", "Las Cruces"],
    "NY": ["New York", "Buffalo", "Rochester", "Albany", "Syracuse", "White Plains"],
    "NC": ["Charlotte", "Raleigh", "Durham", "Greensboro", "Wilmington", "Asheville"],
    "ND": ["Fargo", "Bismarck", "Grand Forks"],
    "OH": ["Columbus", "Cleveland", "Cincinnati", "Dayton", "Toledo", "Akron"],
    "OK": ["Oklahoma City", "Tulsa", "Norman", "Edmond"],
    "OR": ["Portland", "Salem", "Eugene", "Bend"],
    "PA": ["Philadelphia", "Pittsburgh", "Harrisburg", "Allentown", "Lancaster"],
    "RI": ["Providence", "Warwick", "Cranston"],
    "SC": ["Charleston", "Columbia", "Greenville", "Myrtle Beach"],
    "SD": ["Sioux Falls", "Rapid City"],
    "TN": ["Nashville", "Memphis", "Knoxville", "Chattanooga", "Murfreesboro"],
    "TX": ["Houston", "Dallas", "Austin", "San Antonio", "Fort Worth", "El Paso", "Arlington", "Plano", "Frisco"],
    "UT": ["Salt Lake City", "Provo", "Ogden", "St. George"],
    "VT": ["Burlington", "South Burlington", "Rutland"],
    "VA": ["Virginia Beach", "Richmond", "Arlington", "Norfolk", "Alexandria", "Charlottesville"],
    "WA": ["Seattle", "Spokane", "Tacoma", "Bellevue", "Olympia"],
    "WV": ["Charleston", "Huntington", "Morgantown"],
    "WI": ["Milwaukee", "Madison", "Green Bay", "Kenosha"],
    "WY": ["Cheyenne", "Casper", "Laramie"],
    "DC": ["Washington"],
}
