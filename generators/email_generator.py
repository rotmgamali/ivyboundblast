import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import urllib3
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import pytz

# Suppress SSL warnings from scraper to keep logs clean
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import re
import json
from mailreef_automation.logger_util import get_logger

# Add project root to path to allow imports from sibling directories
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

load_dotenv()
_logger = get_logger("EMAIL_GENERATOR")

# Try to import scrapers
try:
    import automation_scrapers.school_scraper as school_scraper
    _logger.info("✓ Successfully imported school_scraper")
except ImportError:
    school_scraper = None

try:
    import automation_scrapers.b2b_scraper as b2b_scraper
    _logger.info("✓ Successfully imported b2b_scraper")
except ImportError:
    b2b_scraper = None

class EmailGenerator:
    """
    Generates hyper-personalized email content using OpenAI + Live Website Scraping.
    Uses 'Archetypes' to select the correct template folder (e.g. /principal).
    """

    # Placeholder/generic titles set by the harvester when no real title was
    # found. Treated as if the title were blank, both for the catch-all skip
    # and for greeting selection (so we never emit "Hi Office," / "Hi Administrator,").
    PLACEHOLDER_TITLES = {
        "office", "staff", "team", "general", "unknown", "n/a", "na",
        "administrator", "admin", "contact", "info",
    }

    # Mapping of role keywords to template folders
    ARCHETYPES = {
        "principal": ["principal", "assistant principal", "vice principal"],
        "head_of_school": ["head of school", "headmaster", "headmistress", "head of", "president", "superintendent"],
        "academic_dean": ["dean", "academic", "curriculum", "instruction"],
        "college_counseling": ["counselor", "college", "guidance", "advisor"],
        "business_manager": ["business", "finance", "cfo", "bursar", "operations"],
        "faith_leader": ["pastor", "minister", "chaplain", "campus ministry", "religious", "father", "reverend"],
        "athletics": ["athletic", "coach", "sports", "physical education"],
        "admissions": ["admission", "enrollment", "registrar"]
    }

    def __init__(self, client=None, templates_dir="templates", log_file="automation.log", archetypes: dict = None):
        self.client = client or OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Support both 'templates' (relative to root) and absolute paths
        if os.path.isabs(templates_dir):
            self.templates_dir = Path(templates_dir)
        else:
            self.templates_dir = BASE_DIR / templates_dir
            
        # Dynamically load archetypes, default to school ones if not provided
        self.archetypes = archetypes or {
            "principal": ["principal", "assistant principal", "vice principal"],
            "head_of_school": ["head of school", "headmaster", "headmistress", "head of", "president", "superintendent"],
            "academic_dean": ["dean", "academic", "curriculum", "instruction"],
            "college_counseling": ["counselor", "college", "guidance", "advisor"],
            "business_manager": ["business", "finance", "cfo", "bursar", "operations"],
            "faith_leader": ["pastor", "minister", "chaplain", "campus ministry", "religious", "father", "reverend"],
            "athletics": ["athletic", "coach", "sports", "physical education"],
            "admissions": ["admission", "enrollment", "registrar"]
        }
            
            
        # --- LOGGING ISOLATION ---
        self.logger = get_logger("EMAIL_GENERATOR", log_file)
        # Avoid removing handlers from a shared logger name if we can avoid it, 
        # but if we must isolate, we do it in self.logger

    def generate_email(
        self,
        campaign_type: str,
        sequence_number: int,
        lead_data: dict,
        enrichment_data: dict,
        sender_email: str = None
    ) -> dict:
        """
        Routing method:
        - If 'school' or 'b2b', use the Archetype + Scraper logic.
        - Otherwise, use legacy dictionary prompts.
        """
        if campaign_type in ["school", "b2b", "crypto"]:
            return self._generate_templated_email(campaign_type, sequence_number, lead_data, enrichment_data, sender_email)
        else:
            return self._generate_legacy_email(campaign_type, sequence_number, lead_data, enrichment_data)

    def _generate_templated_email(self, campaign_type: str, sequence_number: int, lead_data: dict, enrichment_data: dict, sender_email: str = None) -> dict:
        """
        1. Identify Archetype (Role).
        2. Load Template (file).
        3. Domain Guard: Verify email matches website.
        4. Scrape Website (if not already cached).
        5. Generate Email via LLM.
        """
        email = lead_data.get("email", "")
        url = lead_data.get("website") or lead_data.get("domain")

        # --- Personalization Floor ---
        # For SCHOOL campaigns: skip catch-all addresses (info@, contact@, hello@)
        # with no first_name and no real title — sending a "hyper-personalized"
        # pitch to them produces a generic email branded as personal.
        # For B2B campaigns: catch-alls are unavoidable (executives hide their
        # real emails). The b2b scraper extracts rich company context (services,
        # founded year, leadership) so even a "Hi {company} team," email has
        # genuine personalization — let it through.
        local_part = email.split("@", 1)[0].lower() if "@" in email else ""
        first_name = (lead_data.get("first_name") or "").strip()
        raw_title = (lead_data.get("title") or lead_data.get("role") or "").strip()
        title = "" if raw_title.lower() in self.PLACEHOLDER_TITLES else raw_title
        CATCH_ALL_PREFIXES = {
            "info", "contact", "hello", "team", "office", "admin", "support",
            "inquiries", "enquiries", "general", "mail", "email", "hi", "ask",
            "sales", "marketing", "press", "media", "service", "services",
        }
        if (
            campaign_type == "school"
            and local_part in CATCH_ALL_PREFIXES
            and not first_name
            and not title
        ):
            self.logger.warning(
                f"🚫 [PERSONALIZATION FLOOR] Skipping catch-all school lead with no name/title: {email} (raw_title='{raw_title}')"
            )
            return {
                "subject": "SKIP_LEAD",
                "body": "Validation Failed: Catch-all email with no personalization data",
            }

        # --- Institution Type Guard (Strict K-12 Filter) ---
        # Skip this filter for crypto campaigns — only applies to school outreach
        if campaign_type == "school":
            EXCLUDED_KEYWORDS = [
                'surf school', 'flight school', 'preschool', 'pre-school', 'university',
                'gym ', 'dance studio', 'martial arts', 'childcare', 'daycare', 'early learning',
                'nursery', 'ballet school', 'yoga studio', 'tennis academy', 'soccer academy',
                'swimming school', 'driving school', 'learning center', 'academy of art',
                'beauty academy', 'kindergarten only'
            ]
            # Only check school name, not role (avoid false positives like "College Counselor")
            school_name = (lead_data.get("school_name") or "").lower()

            if any(keyword in school_name for keyword in EXCLUDED_KEYWORDS):
                self.logger.warning(f"🚫 [INSTITUTION GUARD] Skipping non-traditional lead: {full_text}")
                return {
                    "subject": "SKIP_LEAD",
                    "body": "Validation Failed: Non-Traditional Institution (Not K-12 Middle/High School)"
                }

        # --- 1. Identify Archetype ---
        role = (lead_data.get("role") or "").lower()
        role_clean = role.strip()
        archetype = self._get_archetype(role_clean)
        _logger.debug(f"🎯 [GEN] {campaign_type.upper()} Archetype: {archetype} (detected from role: '{role_clean}')")
        
        # --- 2. Load Template ---
        template_content = self._load_template_file(campaign_type, archetype, sequence_number)
        
        # Fallback to general if not found and archetype isn't already general
        if not template_content and archetype != "general":
            _logger.debug(f"ℹ️ Template for {archetype}/{sequence_number} not found. Falling back to general.")
            template_content = self._load_template_file(campaign_type, "general", sequence_number)
            
        if not template_content:
            _logger.error(f"❌ Template missing for {campaign_type}/{archetype}/{sequence_number} and fallback general failed.")
            return {"subject": "Quick question", "body": "I'd love to connect regarding your current operations."}

        # --- 3. Smart Website Scraping ---
        school_research = enrichment_data.get("school_research", {})
        website_content = enrichment_data.get("website_content", "")

        if not school_research and not website_content and url:
            if "google.com" in url.lower() or "goo.gl" in url.lower():
                self.logger.warning(f"⚠️ Skipping scrape for Google URL: {url}")
                school_research = {}
            else:
                try:
                    if not url.startswith("http"):
                        url = "https://" + url
                    # Route by campaign type: schools want mission/programs/athletics,
                    # B2B wants company description / services / leadership / about.
                    if campaign_type == "b2b":
                        school_research = self._b2b_scrape(url)
                        scrape_label = "B2B SCRAPE"
                    else:
                        school_research = self._smart_scrape(url)
                        scrape_label = "SMART SCRAPE"
                    website_content = school_research.get("raw", "")
                    non_empty = sum(1 for k, v in school_research.items() if v and k != "raw")
                    self.logger.info(f"✅ [{scrape_label}] Extracted {non_empty} structured fields from {url}")
                except Exception as e:
                    self.logger.error(f"❌ [SCRAPE ERROR] Failed for {url}: {e}")
                    school_research = {}

        # --- 4. Domain Guard & Verification (DEACTIVATED) ---
        # if email and url:
        #     is_valid, reason = self._validate_domain_association(email, url, website_content, lead_data)
        #     if not is_valid:
        #         self.logger.warning(f"🚫 [DOMAIN GUARD] Skipping {email}: {reason}")
        #         return {
        #             "subject": "SKIP_LEAD",
        #             "body": f"Validation Failed: {reason}"
        #         }
        #     self.logger.info(f"🛡️ [DOMAIN GUARD] Verified: {reason}")
        
        # Parse Custom Data
        custom_json = lead_data.get("custom_data", "{}")
        custom_context = ""
        try:
            if isinstance(custom_json, str) and custom_json.strip():
                import json
                data = json.loads(custom_json)
                
                # Extract valuable fields
                desc = data.get("company_insights.description") or data.get("description") or ""
                year = data.get("company_insights.founded_year") or data.get("founded_year")
                reviews = data.get("reviews")
                rating = data.get("rating")
                city = data.get("city") or data.get("company_insights.city")
                
                context_parts = []
                if desc: context_parts.append(f"Business Description: {desc}")
                if year: context_parts.append(f"Founded: {year}")
                if reviews and rating: context_parts.append(f"Reputation: {rating} stars from {reviews} reviews")
                if city: context_parts.append(f"Location: {city}")
                
                if context_parts:
                    custom_context = "\n".join(context_parts)
                    self.logger.debug(f"✅ [DATA] Extracted rich personalization details: {len(context_parts)} items.")
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to parse custom_data: {e}")

        # Build Prompts (System + User)
        system_prompt, user_prompt, envelope = self._prepare_templated_prompts(
            campaign_type, template_content, lead_data, website_content, sequence_number, sender_email, custom_context, school_research
        )

        # Call LLM for Body & Subject; on hallucination, retry once with a
        # stricter system prompt; on second failure, use the raw template body.
        llm_result = self._call_llm(user_prompt, system_prompt)
        candidate = self._strip_hallucinations(llm_result.get("body", ""), envelope["greeting"], envelope["sign_off"])

        ok, reason = self._validate_email_body(
            candidate, template_content, lead_data, custom_context, school_research, website_content
        )
        if not ok:
            self.logger.warning(f"⚠️ [HALLUCINATION] Rejected first draft for {lead_data.get('email')}: {reason}. Retrying.")
            stricter_system = (
                system_prompt
                + "\n\nSTRICT MODE: Do NOT invent statistics, dollar amounts, percentages, "
                "student counts, school details, or program features. Use ONLY facts that appear "
                "in the template or in the research provided. If you cannot personalize without "
                "inventing, write a clean professional pitch using only the offer details from the template."
            )
            llm_result = self._call_llm(user_prompt, stricter_system)
            candidate = self._strip_hallucinations(llm_result.get("body", ""), envelope["greeting"], envelope["sign_off"])
            ok, reason = self._validate_email_body(
                candidate, template_content, lead_data, custom_context, school_research, website_content
            )
            if not ok:
                self.logger.warning(
                    f"⚠️ [HALLUCINATION] Retry also failed for {lead_data.get('email')}: {reason}. "
                    f"Falling back to raw template body."
                )
                # Build a clean subject by trying real subject_patterns from
                # the campaign profile, then stripping any remaining template
                # variables / unfilled placeholders from the body fallback.
                fallback_subj = envelope.get("subject", "")
                if "{{" in fallback_subj or not fallback_subj.strip() or fallback_subj.strip() == "Subject:":
                    patterns = (getattr(self, "profile_config", {}) or {}).get("subject_patterns", [])
                    company_name = lead_data.get("school_name") or lead_data.get("company_name") or ""
                    pick = next((p for p in patterns if "{{" not in p), None) or "Quick question"
                    if "{{ company_name }}" in pick and company_name:
                        pick = pick.replace("{{ company_name }}", company_name)
                    if "Quick question" in pick and company_name:
                        pick = f"Quick question about {company_name}"
                    fallback_subj = pick
                # Strip remaining template variables / placeholders / leftover Subject line
                fallback = self._TEMPLATE_VAR_RE.sub("", template_content or "").strip()
                fallback = self._PLACEHOLDER_RE.sub("", fallback).strip()
                fallback = re.sub(r"(?im)^\s*Subject:.*$\n?", "", fallback).strip()
                # Drop any leading/trailing greeting/sign-off lines from the
                # template since the envelope adds those back.
                fallback = re.sub(r"^(?i)(?:Hi|Dear|Good|Hello|To the).*?,\s*\n+", "", fallback).strip()
                # Collapse runs of double-spaces from removed placeholders
                fallback = re.sub(r" {2,}", " ", fallback)
                candidate = fallback
                llm_result = {"subject": fallback_subj or "Quick question", "body": candidate}
        clean_body = candidate
        
        # FINAL PROTECTION: Ensure no "Hi [Name]" if we already have it in clean_body
        final_greeting = envelope['greeting']
        if clean_body.lower().startswith("hi ") or clean_body.lower().startswith("good "):
            # AI hallucinated a greeting, let's just use the AI's if it's there, 
            # or trust our deterministic one. Deterministic is safer.
            first_line = clean_body.split('\n')[0]
            if "," in first_line and len(first_line) < 30:
                clean_body = "\n".join(clean_body.split('\n')[1:]).strip()

        final_body = f"{final_greeting}\n\n{clean_body}\n\n{envelope['sign_off']}"
        
        return {
            "subject": llm_result.get('subject') or envelope['subject'],
            "body": final_body
        }

    def _smart_scrape(self, url: str) -> dict:
        """Extract structured school data from website instead of raw text dump."""
        import requests
        from bs4 import BeautifulSoup
        result = {"raw": "", "mission": "", "programs": "", "athletics": "", "achievements": "", "mascot": "", "enrollment": "", "faith": ""}

        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=15, verify=False)
            if response.status_code != 200:
                return result

            soup = BeautifulSoup(response.text, 'html.parser')
            # Remove noise elements
            for tag in soup(["script", "style", "nav", "footer", "header", "iframe", "noscript"]):
                tag.decompose()

            text = soup.get_text(separator='\n')
            lines = [line.strip() for line in text.splitlines() if line.strip() and len(line.strip()) > 10]
            clean_text = '\n'.join(lines)
            result["raw"] = clean_text[:3000]

            text_lower = clean_text.lower()

            # Extract mission statement
            for keyword in ["our mission", "mission statement", "about us", "our story", "who we are", "our vision"]:
                idx = text_lower.find(keyword)
                if idx != -1:
                    chunk = clean_text[idx:idx+500]
                    sentences = chunk.split('.')[:3]
                    result["mission"] = '.'.join(sentences).strip()[:400]
                    break

            # Extract academic programs
            program_keywords = ["ap course", "ib program", "honors", "stem", "dual enrollment", "college prep",
                                "advanced placement", "curriculum", "academic program", "magnet"]
            program_hits = []
            for kw in program_keywords:
                idx = text_lower.find(kw)
                if idx != -1:
                    start = max(0, idx - 50)
                    program_hits.append(clean_text[start:idx+200].strip())
            if program_hits:
                result["programs"] = ' | '.join(program_hits[:3])[:500]

            # Extract athletics/mascot
            for kw in ["athletics", "varsity", "sports program", "our teams", "go "]:
                idx = text_lower.find(kw)
                if idx != -1:
                    result["athletics"] = clean_text[idx:idx+300].strip()[:300]
                    break

            # Mascot detection
            import re as _re
            mascot_match = _re.search(r'(?:go|home of the|we are the)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', clean_text)
            if mascot_match:
                result["mascot"] = mascot_match.group(1).strip()

            # Extract achievements
            for kw in ["award", "recognition", "ranked", "named", "accreditation", "blue ribbon", "honor roll"]:
                idx = text_lower.find(kw)
                if idx != -1:
                    result["achievements"] = clean_text[max(0,idx-30):idx+250].strip()[:300]
                    break

            # Extract enrollment/size
            enrollment_match = _re.search(r'(\d{2,4})\s*(?:students|enrolled|families|boys and girls)', clean_text, _re.IGNORECASE)
            if enrollment_match:
                result["enrollment"] = enrollment_match.group(0).strip()

            # Detect faith affiliation
            faith_keywords = ["christian", "catholic", "lutheran", "jewish", "montessori", "baptist", "episcopal",
                              "methodist", "adventist", "islamic", "faith-based", "church", "ministry"]
            for fk in faith_keywords:
                if fk in text_lower:
                    result["faith"] = fk.title()
                    break

            # If homepage was thin, try /about page
            if len(result["mission"]) < 50 and len(result["programs"]) < 50:
                try:
                    about_url = url.rstrip('/') + '/about'
                    resp2 = requests.get(about_url, headers=headers, timeout=10, verify=False)
                    if resp2.status_code == 200:
                        soup2 = BeautifulSoup(resp2.text, 'html.parser')
                        for tag in soup2(["script", "style", "nav", "footer", "header"]):
                            tag.decompose()
                        about_text = soup2.get_text(separator='\n')
                        about_lower = about_text.lower()
                        for keyword in ["our mission", "mission statement", "about us", "who we are"]:
                            idx = about_lower.find(keyword)
                            if idx != -1:
                                chunk = about_text[idx:idx+500]
                                sentences = chunk.split('.')[:3]
                                result["mission"] = '.'.join(sentences).strip()[:400]
                                break
                except Exception:
                    pass

        except Exception as e:
            self.logger.error(f"Smart scrape failed for {url}: {e}")

        return result

    def _b2b_scrape(self, url: str) -> dict:
        """Extract B2B-shaped facts from a company website (description, what
        they do, who runs it, where they are). Mirrors _smart_scrape's signature
        so the generator's prompt-builder can consume it the same way."""
        import requests
        from bs4 import BeautifulSoup
        import re as _re

        result = {
            "raw": "",
            "mission": "",        # tagline / "about us" blurb
            "programs": "",       # services / what they do
            "achievements": "",   # awards / recognition
            "enrollment": "",     # company size / "Nx employees" / "founded"
            "faith": "",          # leadership names if detectable
            "athletics": "",      # industry / category
            "mascot": "",         # company name (from <title>)
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        def _clean_soup_text(soup) -> str:
            for tag in soup(["script", "style", "nav", "footer", "header", "iframe", "noscript", "form"]):
                tag.decompose()
            txt = soup.get_text(separator="\n")
            lines = [l.strip() for l in txt.splitlines() if l.strip() and len(l.strip()) > 8]
            return "\n".join(lines)

        try:
            response = requests.get(url, headers=headers, timeout=15, verify=False)
            if response.status_code != 200:
                return result

            soup = BeautifulSoup(response.text, "html.parser")

            # Capture company name from <title> (often "Company Name | Tagline")
            title_tag = soup.find("title")
            if title_tag and title_tag.text:
                title_str = title_tag.text.strip()
                # Trim "| Tagline" or " - Tagline" suffix
                first = _re.split(r"\s+[\|\-–—]\s+", title_str, maxsplit=1)[0].strip()
                if 3 < len(first) < 80:
                    result["mascot"] = first  # reused field: company display name

            # Meta description = best one-line "about us" candidate
            meta_desc = soup.find("meta", attrs={"name": _re.compile("^description$", _re.I)})
            if meta_desc and meta_desc.get("content"):
                result["mission"] = meta_desc["content"].strip()[:400]
            else:
                og_desc = soup.find("meta", attrs={"property": _re.compile("^og:description$", _re.I)})
                if og_desc and og_desc.get("content"):
                    result["mission"] = og_desc["content"].strip()[:400]

            clean_text = _clean_soup_text(soup)
            text_lower = clean_text.lower()
            result["raw"] = clean_text[:3500]

            # Fallback "about us" blurb from body text
            if len(result["mission"]) < 40:
                for keyword in ["about us", "who we are", "our story", "our mission", "what we do", "our company"]:
                    idx = text_lower.find(keyword)
                    if idx != -1:
                        chunk = clean_text[idx:idx + 600]
                        sentences = [s.strip() for s in chunk.split(".") if len(s.strip()) > 20][:3]
                        if sentences:
                            result["mission"] = ". ".join(sentences)[:400]
                        break

            # Services / "what they do"
            service_kws = [
                "our services", "what we offer", "what we do", "products", "solutions",
                "services include", "specializing in", "we provide", "expertise",
            ]
            for kw in service_kws:
                idx = text_lower.find(kw)
                if idx != -1:
                    result["programs"] = clean_text[idx:idx + 350].strip()[:350]
                    break

            # Founded year
            founded_match = _re.search(
                r"(?:founded|established|since|est\.?|operating since)\s*(?:in\s+)?(?:the\s+year\s+)?(\d{4})",
                text_lower,
            )
            if founded_match:
                year = founded_match.group(1)
                # Reject obviously wrong (e.g. parsing "200 customers" as year)
                if 1850 <= int(year) <= 2026:
                    result["enrollment"] = f"Founded {year}"

            # Employee count / size
            size_match = _re.search(
                r"(\d{2,5}(?:,\d{3})?)\s*(?:employees|team members|professionals|people|associates)",
                clean_text,
                _re.IGNORECASE,
            )
            if size_match:
                size_str = size_match.group(0).strip()
                if result["enrollment"]:
                    result["enrollment"] = f"{result['enrollment']} | {size_str}"
                else:
                    result["enrollment"] = size_str

            # Awards / accolades
            for kw in ["award", "recognition", "ranked", "featured in", "voted", "best of",
                       "as seen in", "named one of", "accreditation"]:
                idx = text_lower.find(kw)
                if idx != -1:
                    result["achievements"] = clean_text[max(0, idx - 30):idx + 250].strip()[:300]
                    break

            # Industry hint — pick first category-ish keyword present
            industry_kws = [
                "manufacturing", "real estate", "law firm", "consulting", "marketing",
                "construction", "logistics", "healthcare", "technology", "software",
                "finance", "insurance", "hospitality", "retail", "wholesale", "design",
                "engineering", "research", "agency",
            ]
            hits = [kw for kw in industry_kws if kw in text_lower]
            if hits:
                result["athletics"] = ", ".join(hits[:3]).title()

            # Leadership / founder names — look for "Founded by X" / "CEO X" patterns
            leader_match = _re.search(
                r"(?:founded by|ceo|founder|president|managing partner|managing director)\s*[:\-,]?\s*([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)",
                clean_text,
            )
            if leader_match:
                result["faith"] = leader_match.group(1).strip()  # reused: leadership name

            # If homepage was thin, try /about
            if len(result["mission"]) < 60 and len(result["programs"]) < 60:
                for path in ("/about", "/about-us", "/company", "/our-story"):
                    try:
                        about_url = url.rstrip("/") + path
                        resp2 = requests.get(about_url, headers=headers, timeout=10, verify=False)
                        if resp2.status_code != 200:
                            continue
                        soup2 = BeautifulSoup(resp2.text, "html.parser")
                        about_text = _clean_soup_text(soup2)
                        about_lower = about_text.lower()
                        for keyword in ["our mission", "about us", "who we are", "our story", "what we do"]:
                            idx = about_lower.find(keyword)
                            if idx != -1:
                                chunk = about_text[idx:idx + 600]
                                sentences = [s.strip() for s in chunk.split(".") if len(s.strip()) > 20][:3]
                                if sentences:
                                    result["mission"] = ". ".join(sentences)[:400]
                                break
                        if result["mission"]:
                            break
                    except Exception:
                        continue

        except Exception as e:
            self.logger.error(f"B2B scrape failed for {url}: {e}")

        return result

    def _fallback_scrape(self, url: str) -> str:
        """Legacy scraper — returns raw text. Use _smart_scrape instead."""
        data = self._smart_scrape(url)
        return data.get("raw", "")

    def _get_archetype(self, role: str) -> str:
        """Map job title to archetype folder name."""
        for key, keywords in self.archetypes.items():
            if any(k in role for k in keywords):
                return key
        return "general"  # Default

    def _validate_domain_association(self, email: str, url: str, website_text: str, lead_data: dict) -> tuple:
        """
        Verify that the email domain matches the website domain.
        If it's a generic domain (gmail/outlook) or mismatch, use AI to verify context.
        """
        email_domain = email.split("@")[-1].lower() if "@" in email else ""
        
        # Extract base domain from URL
        clean_url = url.lower().replace("http://", "").replace("https://", "").replace("www.", "").split("/")[0]
        url_domain = clean_url
        
        # 1. Direct Match Check
        if email_domain == url_domain or url_domain.endswith(f".{email_domain}") or email_domain.endswith(f".{url_domain}"):
            return True, f"Domain Match: {email_domain} == {url_domain}"

        # 2. Generic Provider Exception
        generics = ["gmail.com", "outlook.com", "hotmail.com", "yahoo.com", "icloud.com", "me.com"]
        
        # 3. AI Context Verification
        self.logger.info(f"❓ [DOMAIN GUARD] Non-matching domain ({email_domain} vs {url_domain}). Verifying via AI...")
        
        first_name = lead_data.get("first_name", "")
        last_name = lead_data.get("last_name", "")
        role = lead_data.get("role", "staff")
        
        verify_prompt = f"""You are a Lead Verification Agent.
Your job is to determine if a person's email is likely associated with a specific school website.

PERSON: {first_name} {last_name}
ROLE: {role}
EMAIL: {email}
WEBSITE: {url}

WEBSITE TEXT (Snippet):
'''
{website_text[:4000]}
'''

TASK:
Can you find evidence that this person ({first_name} {last_name}) or their role ({role}) exists at this school?
Or does the email domain ({email_domain}) appear anywhere in the text as an official contact?

Respond in JSON only:
{{
  "verified": true/false,
  "confidence": 0-1,
  "reason": "short explanation"
}}
"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": verify_prompt}],
                response_format={ "type": "json_object" },
                temperature=0
            )
            result = json.loads(response.choices[0].message.content)
            
            if result.get("verified") and result.get("confidence", 0) > 0.7:
                return True, f"AI Verified: {result.get('reason')}"
            else:
                return False, f"AI Rejected: {result.get('reason')}"
        except Exception as e:
            self.logger.error(f"Error during AI Domain Verification: {e}")
            # Fallback: if it's a generic email but we have a strong name match? 
            # For safety, we reject if AI fails/unsure.
            return False, f"Verification Error: {str(e)}"

    def _sanitize_name(self, name: str, lead_data: dict) -> str:
        """Sanitize first name to avoid 'Hi Harvest' or 'Hi Info'."""
        if not name: return ""
        name = name.strip()
        lower_name = name.lower()
        
        # Blocklist (expanded to catch common placeholder terms)
        blocklist = [
            "info", "admin", "administrator", "office", "contact", 
            "admissions", "principal", "head", "school", "manager",
            "leader", "team", "coordinator", "assistant", "staff"
        ]
        if any(term in lower_name for term in blocklist):
            return ""
            
        # Check against School Name
        school_name = lead_data.get("school_name", "").lower()
        if school_name:
            # If name is just the first word of school (REMOVED: Too aggressive, blocks 'Viva')
            # school_parts = school_name.split()
            # if school_parts and lower_name == school_parts[0]:
            #    return ""
            # If name matches the school name exactly
            if lower_name == school_name:
                return ""
                
        # Strip trailing punctuation (common in "Last, First" data)
        name = name.rstrip(",. ")
        
        return name

    def _get_time_greeting(self) -> str:
        """Return Good morning/afternoon/evening based on EST time."""
        try:
            est = pytz.timezone('US/Eastern')
            now = datetime.now(est)
            hour = now.hour
            
            if 5 <= hour < 12:
                return "Good morning"
            elif 12 <= hour < 17:
                return "Good afternoon"
            else:
                return "Good evening"
        except Exception:
            return "Good day"

    def _load_template_file(self, campaign_type: str, archetype: str, sequence_number: int) -> Optional[str]:
        """Read template file from disk (e.g. templates/school/principal/email_1.txt)."""
        # Map sequence number to file name (email_1.txt)
        filename = f"email_{sequence_number}.txt"
        # First try: templates_dir / campaign_type / archetype (for shared templates_dir like "templates")
        path = self.templates_dir / campaign_type / archetype / filename
        # Second try: templates_dir / archetype (if templates_dir already includes campaign_type, e.g. "templates/crypto")
        path_short = self.templates_dir / archetype / filename

        _logger.debug(f"🔍 [PATH CHECK] Looking for template at: {path} or {path_short}")

        if not path.exists() and path_short.exists():
            path = path_short
        
        if path.exists():
            content = path.read_text(encoding="utf-8")
            self.logger.info(f"📄 [TEMPLATE CONTENT PREVIEW] {content[:100]}...")
            return content
        
        # Diagnostic: List files to see what's actually there
        try:
            if self.templates_dir.exists():
                contents = os.listdir(self.templates_dir)
                self.logger.debug(f"📁 [DIR LIST] Content of {self.templates_dir}: {contents}")
            else:
                self.logger.error(f"🚨 [DIR MISSING] Template directory NOT FOUND at {self.templates_dir}")
        except Exception as e:
            self.logger.debug(f"🔍 [DIR ERROR] Could not list directory: {e}")
            
        return None

    def _prepare_templated_prompts(self, campaign_type: str, template_content: str, lead_data: dict, website_content: str, sequence_number: int, sender_email: str, custom_context: str = "", school_research: dict = None) -> tuple:
        """
        Constructs (system_message, user_message, envelope_dict).
        Implements the ENVELOPE PATTERN: 
        - Calculates Greeting/Sign-off in Python.
        - Strips them from the template.
        - Asks LLM for BODY ONLY.
        """
        
        # --- 1. Calculate Variables (Identity & Recipient) ---
        
        # Name & Greeting Logic
        raw_name = lead_data.get("first_name", "")
        # ... (retained logic) ...
        # (This tool call needs to be precise so I don't delete the whole body. Let's act on the signature first)
        
        # (Actually, I need to jump down to where user_prompt is constructed to inject custom_context)
        # Let's do this in two chunks if needed, or target the prompt construction block.
        pass

    # I will split this into two calls for safety. First the signature.
    # Wait, I can't use `pass` in replacement. I need to be exact.
    # I will target the signature line specifically.

        
        # Name & Greeting Logic
        raw_name = lead_data.get("first_name", "")
        role = lead_data.get("role", "").strip()
        school_name = lead_data.get("school_name") or lead_data.get("company_name") or "your school"

        # For crypto campaigns, skip the school name sanitizer — channel names ARE valid names
        if campaign_type == "crypto":
            sanitized = raw_name.strip() if raw_name else ""
        else:
            sanitized = self._sanitize_name(raw_name, lead_data)

        if sanitized:
            first_name = sanitized
            if campaign_type != "crypto":
                # Religious Titles (school campaigns only)
                role_lower = role.lower()
                religious_titles = {"pastor": "Pastor", "reverend": "Reverend", "rev.": "Reverend", "father": "Father", "rabbi": "Rabbi"}
                for keyword, title in religious_titles.items():
                    if keyword in role_lower and title.lower() not in first_name.lower():
                        first_name = f"{title} {first_name}"
                        break
            greeting_line = f"Hey {first_name}," if campaign_type == "crypto" else f"Hi {first_name},"
        elif (
            role
            and len(role) > 2
            and role.lower() not in {"high school", "middle school", "elementary school", "pk-12", "preschool", "academy"}
            and role.lower() not in self.PLACEHOLDER_TITLES
        ):
            # Fallback to Role-based (e.g. Hi Principal,) — but never for
            # placeholder titles like "Office" / "Administrator" / "Staff",
            # which would produce awkward greetings like "Hi Office,".
            first_name = role.title()
            greeting_line = f"Hey {first_name}," if campaign_type == "crypto" else f"Hi {first_name},"
        elif school_name and school_name.lower() != "your school":
            # Fallback to org name
            greeting_line = f"Hey {school_name} team," if campaign_type == "crypto" else f"To the {school_name} Team,"
            first_name = "Team"
        else:
            # Absolute fallback
            if campaign_type == "crypto":
                greeting_line = "Hey,"
                first_name = ""
            else:
                greeting_line = "Hi,"
                first_name = "School Leader"

        # Sender Identity (from config — supports per-campaign override)
        sender_identities = None
        sender_company = "Ivybound Education Partners"
        try:
            from mailreef_automation import automation_config as _ac
            override_name = (self.profile_config or {}).get("sender_identities_override") if hasattr(self, "profile_config") and self.profile_config else None
            if override_name and hasattr(_ac, override_name):
                sender_identities = getattr(_ac, override_name)
            else:
                sender_identities = _ac.SENDER_IDENTITIES
        except Exception:
            sender_identities = {"default": {"name": "Andrew Rollins", "title": "Ivybound Education Partners"}}

        if campaign_type == "crypto":
            sender_name = "Andrew"
        else:
            sender_identity = sender_identities.get("default", {})
            if sender_email:
                local_part = sender_email.split("@")[0].lower() if "@" in sender_email else ""
                for key in sender_identities:
                    if key in local_part:
                        sender_identity = sender_identities[key]
                        break
            sender_name = sender_identity.get("name", "Andrew Rollins")
            sender_company = sender_identity.get("title", sender_company)
        
        
        # --- 2. Python-Side Template Substitution (The Fix) ---
        # Regex replacement for robust handling of {{name}} vs {{ name }}
        # 1. Replace Greeting
        # We want to replace the entire "Hi {{ first_name }}," block matches if possible, 
        # or just the variable.
        
        draft_body = template_content
        
        # Strategy: Pre-fill ALL known variables in the template so the LLM sees clean text.
        school_name = lead_data.get("school_name") or lead_data.get("company_name") or "your company"
        school_type = lead_data.get("school_type", "private").lower()
        
        replacements = {
            "first_name": first_name,
            "school_name": school_name,
            "company_name": school_name, # Alias for B2B
            "city": lead_data.get("city", "your city"),
            "state": lead_data.get("state", ""),
            "role": lead_data.get("role", "executive"),
            "greeting": greeting_line # Expose the calculated greeting (e.g. "Good morning," or "Hi Andrew,")
        }
        
        # 1. Replace Greeting Variable
        # Template uses {{ greeting }}
        # Logic: Replace "{{ greeting }}" with the computed line and ensures no double punctuation
        if "{{ greeting }}" in draft_body:
            draft_body = draft_body.replace("{{ greeting }}", greeting_line)
        
        # 2. Replace other variables (school_name, etc)
        for key, val in replacements.items():
            if key == "greeting": continue # Already handled
            pattern = re.compile(r'\{\{\s*' + key + r'\s*\}\}', re.IGNORECASE)
            draft_body = pattern.sub(str(val), draft_body)
             
        # --- 3. Template Stripping (The Cleaning) ---
        # We need to give the AI only the BODY text to transform.
        # We must strip the Subject line and the Greeting line.
        
        # Extract and save the exact Subject line from the template before stripping it
        subject_match = re.search(r'(?i)^Subject:\s*(.*)', draft_body)
        template_subject = subject_match.group(1).strip() if subject_match else "Quick question"

        # Remove Subject line
        clean_draft = re.sub(r'(?i)^Subject:.*?\n+', '', draft_body).strip()
        
        # Remove Greeting line (e.g. "Hi Andrew," or "Good morning,")
        # Matches a greeting at the very start of the (now subject-less) draft
        clean_draft = re.sub(r'^(?i)(?:Hi|Dear|Good|Hello).*?,\s*\n+', '', clean_draft).strip()
        
        # Strip Sign-off from bottom of draft
        # Markers: Best, Sincerely, etc. or the sender's own name
        for marker in ["Best,", "Sincerely,", "Warmly,", "Cheers,", "Thanks,", sender_name]:
             if marker in clean_draft:
                  # Take only what's before the last occurrence of the marker to be safe
                  parts = clean_draft.rsplit(marker, 1)
                  clean_draft = parts[0].strip()
        
        # --- 4. Envelope Definition ---
        # Define the deterministic shell. Include company line so brand is correct
        # for non-Ivybound campaigns (e.g. SerenitySpaces Bahamas).
        sign_off_block = f"Best,\n{sender_name}\n{sender_company}"
        envelope = {
            "greeting": greeting_line,
            "sign_off": sign_off_block,
            "subject": template_subject # Default, AI will override if instructed
        }
        
        # --- 5. System Prompt (Constraint) ---
        if campaign_type == "crypto":
            system_prompt = f"""You are {sender_name}, founder of Demons & Deities, a TFT-style auto-battler NFT game on Polygon.

STYLE GUIDE:
- Tone: Casual, confident, like texting someone you respect but don't know yet. NOT corporate.
- Write like a real person — short sentences, no buzzwords, no "I'd love to" or "I noticed that" or "caught my eye".
- Formatting: Short paragraphs. Max 4-5 lines of body text total.
- Absolute Rules:
  1. DO NOT include a greeting (e.g. "Hey...").
  2. DO NOT include a sign-off (e.g. "Best, Andrew").
  3. OUTPUT ONLY the Subject and the Body text.
  4. NEVER say "I noticed", "caught my eye", "I was impressed", "I'd love to connect".

PLACEHOLDER POLICY:
- NEVER use brackets or parentheses for unknown data.
- If the research doesn't reveal anything specific, just skip personalization and go straight to the pitch.
"""
        else:
            # Per-campaign system_prompt_template override (e.g. Bahamas retreat)
            profile_prompt = (self.profile_config or {}).get("system_prompt_template") if hasattr(self, "profile_config") and self.profile_config else None
            if profile_prompt:
                try:
                    system_prompt = profile_prompt.format(sender_name=sender_name, sender_company=sender_company)
                except Exception:
                    system_prompt = profile_prompt
                # Skip default school prompt — return early through the existing flow
                # (we still need user_prompt below; jump past the default block)
                school_type = lead_data.get("school_type", "private").lower()
                _profile_prompt_used = True
            else:
                _profile_prompt_used = False

            if not _profile_prompt_used:
                school_type = lead_data.get("school_type", "private").lower()
                system_prompt = f"""You are {sender_name} from Ivybound Education Partners, writing a personal outreach email to a school administrator.

VOICE:
- Write in first person, conversational but professional. Like a real person, not a marketer.
- Short paragraphs. No bullet points in Email 1.
- NEVER use these phrases: "I noticed", "caught my eye", "I'd love to", "reaching out", "touching base", "checking in", "hope this finds you well", "game-changer", "unlock potential", "leverage", "synergy".
- Sound like someone who genuinely read about their school — not someone running a mail merge.

RULES:
1. Do NOT include any greeting (no "Hi Name," or "Good morning,").
2. Do NOT include any sign-off (no "Best," or signature).
3. Output ONLY the Subject line and Body paragraphs.
4. NEVER use placeholder brackets [] or parenthetical placeholders ().
5. If you cannot find a specific detail to reference from the research, write a clean professional email without faking personalization. A genuine pitch is better than fake flattery.

SCHOOL CONTEXT:
- School type: {school_type}
- If PRIVATE: Emphasize enrollment differentiation, prestige, college matriculation, parent value.
- If PUBLIC: Emphasize district alignment, budget efficiency, measurable test score gains.
"""

        # --- 6. User Prompt (Body & Subject Generation) ---
        if not school_research:
            school_research = {}

        if campaign_type == "crypto":
            user_prompt = f"""You are writing a cold email to {first_name} ({role}) at "{school_name}".

RESEARCH ON THEM (scraped from their website/channel):
{website_content[:4500]}

DRAFT EMAIL (your starting point):
'''
{clean_draft}
'''

EXTRA CONTEXT:
{custom_context}

TASK:
    1. SUBJECT LINE: Use "this game shouldn't exist yet" as the subject. Do NOT change it unless the research reveals something so specific that a personalized subject would clearly outperform (e.g. referencing their exact channel name or a project they covered). In that case, keep it under 6 words and mysterious.

    2. FIRST LINE: Write ONE hyper-personalized opening line based on the RESEARCH. Find something SPECIFIC:
       - A video they made, a project they backed, a tweet topic, a client they worked with
       - Write it casually like a text: "your [specific thing] was sick" or "you backed [project] before anyone else"
       - If research is empty or generic, skip personalization entirely — just start with the pitch

    3. REST OF BODY: Keep the core pitch from the DRAFT but make it sound like a human texting. Max 4 lines after the personalized opener. Include the trailer link and the "Want a Founders Pass?" hook.

    4. CONSTRAINTS:
       - NO GREETINGS or SIGN-OFFS
       - NO PLACEHOLDERS like [name] or (company)
       - Total body: 40-60 words MAX. Shorter is better.
       - BANNED PHRASES (never use these): "on point", "impressive", "caught my eye", "I noticed", "I'd love to", "reaching out", "touching base", "always on point", "next level", "incredible", "amazing work"
       - If the RESEARCH section is empty, very short, or just generic website boilerplate (navigation text, cookie notices, footer links) — DO NOT write a personalized first line at all. Just go straight to the pitch. A cold pitch with no personalization is better than fake personalization.
       - CRITICAL: You MUST always include the full pitch (what the game is, the trailer link, and the CTA). Never output just a trailer link with no context. The DRAFT CONTENT contains the minimum — do not remove lines from it, only rephrase them.

    Output format:
    SUBJECT: [subject line]

    BODY: [personalized first line]

    [2-3 lines of pitch]

    [one-line hook/CTA]"""
        else:
            # Build structured research section from smart scraper
            research_lines = []
            if school_research.get("mission"):
                research_lines.append(f"- Mission: {school_research['mission']}")
            if school_research.get("programs"):
                research_lines.append(f"- Programs: {school_research['programs']}")
            if school_research.get("athletics"):
                research_lines.append(f"- Athletics: {school_research['athletics']}")
            if school_research.get("mascot"):
                research_lines.append(f"- Mascot: {school_research['mascot']}")
            if school_research.get("achievements"):
                research_lines.append(f"- Achievements: {school_research['achievements']}")
            if school_research.get("enrollment"):
                research_lines.append(f"- Size: {school_research['enrollment']}")
            if school_research.get("faith"):
                research_lines.append(f"- Affiliation: {school_research['faith']}")

            research_section = '\n'.join(research_lines) if research_lines else "No specific research available — write a clean professional email without faking personalization."

            city = lead_data.get("city", "")
            state = lead_data.get("state", "")
            location = f"{city}, {state}".strip(", ") if city or state else ""

            user_prompt = f"""You are writing to {first_name} ({lead_data.get('role', 'administrator')}) at "{school_name}"{f' in {location}' if location else ''}.

SCHOOL RESEARCH (extracted from their website):
{research_section}

{f'RAW WEBSITE TEXT (backup context):' + chr(10) + website_content[:2000] if not research_lines and website_content else ''}

DRAFT EMAIL TEMPLATE (your starting framework — keep the core pitch intact):
'''
{clean_draft}
'''

{f'ADDITIONAL CONTEXT:' + chr(10) + custom_context if custom_context else ''}

TASK:
1. SUBJECT LINE: Write a 3-6 word subject that feels specific to this school. Examples:
   - "Quick question for {school_name} families"
   - "Go {school_research.get('mascot', 'Eagles')}! + a question"
   - "Question about {school_name}"
   Do NOT use generic phrases like "Scholarship ROI" or "Checking in".

2. PERSONALIZED OPENING (1-2 sentences): Reference ONE specific detail from the research — a program, achievement, mission phrase, athletic team, or faith community. Make it genuine. If research is thin, write a clean professional opener without faking specifics.

3. CORE PITCH: Keep the template's key facts:
   - $375 program price
   - 150+ point average SAT increase
   - $15,000+ in merit aid per student
   - Zero cost to the school
   - 10-minute call CTA

4. CONSTRAINTS:
   - No greetings or sign-offs.
   - No placeholder brackets or parentheses.
   - Total body: 100-140 words.
   - The personalized opening must flow naturally into the pitch.

Output format:
SUBJECT: [subject line]

BODY: [full body text]"""
        return system_prompt, user_prompt, envelope

    # Numbers the LLM is allowed to use without an explicit source. These
    # come from the campaign's own offer (templates) plus harmless years.
    _APPROVED_NUMBERS = {
        "10", "15", "18", "20", "22", "25", "50", "100", "125", "150", "200",
        "250", "300", "375", "500", "650", "675", "850", "1000", "1500", "2000",
        "10000", "125000", "1000000",
    }
    _PLACEHOLDER_RE = re.compile(
        r"\[(?:Name|City|School|Company|Year|N|X|Insert|Specific|Detail|First|Last|Mascot|Number|Stat|"
        r"School Name|Company Name|First Name|Last Name|Date|Day|Month|Time)\b[^\]]*\]",
        re.IGNORECASE,
    )
    _TEMPLATE_VAR_RE = re.compile(r"\{\{[^}]+\}\}|\{[a-zA-Z_]+\}")
    # 2+ digit numbers, optionally with %, +, k/K, m/M, or $ prefix
    _NUMBER_TOKEN_RE = re.compile(r"\$?\d{2,}(?:[,]\d{3})*(?:\.\d+)?[%+kKmM]?")

    def _validate_email_body(
        self,
        body: str,
        template_content: str,
        lead_data: dict,
        custom_context: str,
        school_research: dict,
        website_content: str,
    ) -> tuple[bool, str]:
        """Catch obvious hallucinations: placeholders, length runaways, and
        specific numeric claims that don't appear in any source the AI was
        shown. Returns (is_valid, reason). Reason is "OK" when valid."""
        if not body or not body.strip():
            return False, "empty body"

        word_count = len(body.split())
        if word_count < 50:
            return False, f"too short ({word_count} words)"
        if word_count > 230:
            return False, f"too long ({word_count} words)"

        if self._PLACEHOLDER_RE.search(body):
            return False, "unfilled placeholder bracket"
        if self._TEMPLATE_VAR_RE.search(body):
            return False, "unrendered template variable"

        # Source haystack the AI was actually given. Anything numeric outside
        # this set is suspect.
        try:
            source_blob = " ".join([
                template_content or "",
                json.dumps(lead_data, default=str),
                custom_context or "",
                json.dumps(school_research or {}, default=str),
                (website_content or "")[:6000],
            ]).lower()
        except Exception:
            source_blob = (template_content or "").lower() + " " + (custom_context or "").lower()

        for raw in self._NUMBER_TOKEN_RE.findall(body):
            digits = re.sub(r"[^\d]", "", raw)
            if not digits or len(digits) < 2:
                continue
            n = int(digits)
            # Years are fine
            if 1900 <= n <= 2100:
                continue
            if digits in self._APPROVED_NUMBERS:
                continue
            if digits in source_blob:
                continue
            # Check the raw token (e.g. "$125,000") in the source as written
            if raw.lower() in source_blob:
                continue
            return False, f"fabricated number '{raw}' not in source"

        return True, "OK"

    def _strip_hallucinations(self, body_text: str, greeting: str, sign_off: str) -> str:
        """Failsafe: If AI wrote 'Hi Andrew,' or 'Best, Name' anyway, remove it."""
        lines = body_text.split("\n")
        
        # 1. Strip Leading Greeting — only if first line is SHORT and looks like a greeting
        greeting_markers = ["hi ", "hi,", "dear ", "good morning", "good afternoon", "good evening", "hello ", "hello,", "to the "]
        if lines:
            first_line = lines[0].strip()
            is_greeting = (
                len(first_line) < 50
                and any(first_line.lower().startswith(g) for g in greeting_markers)
                and ("," in first_line or ":" in first_line)
            )
            if is_greeting:
                lines = lines[1:]
                
        # 2. Strip Trailing Sign-off
        # Check last 2-3 lines for sign-off markers
        while lines and not lines[-1].strip(): lines.pop() # Remove trailing empty
        
        if lines:
            last_line = lines[-1].strip().lower()
            # If last line is just a name or a common sign-off
            markers = ["best", "sincerely", "warmly", "cheers", "thanks", "regards", "andrew", "genelle", "mark"]
            if any(last_line == m or last_line.startswith(f"{m},") for m in markers):
                lines.pop()
                # Check one more line up for the "Best," part if it was "Best,\nName"
                if lines:
                    new_last = lines[-1].strip().lower()
                    if any(new_last == m or new_last.startswith(f"{m},") for m in markers):
                        lines.pop()

        body = "\n".join(lines).strip()
        
        # 3. Strip ONLY placeholder brackets/parens — preserve legitimate content
        # Only remove brackets containing placeholder-like text (single words, "Insert X", "Your X")
        body = re.sub(r'\[(?:Name|City|School|Company|Insert|Your|Specific|Detail|School Name|First Name|Mascot)[^\]]*\]', '', body)
        # Only remove parens that look like placeholders, not legitimate content like "(150+ points)"
        body = re.sub(r'\((?:Name|City|School|Company|Insert|Your|Specific|Detail)[^\)]*\)', '', body)

        body = body.replace('  ', ' ').strip()
        
        return body

    def _generate_legacy_email(self, campaign_type: str, sequence_number: int, lead_data: dict, enrichment_data: dict) -> dict:
        """Fallback for non-school campaigns."""
        prompt_key = f"email_{sequence_number}"
        prompts = self.LEGACY_PROMPTS.get(campaign_type, {})
        prompt_template = prompts.get(prompt_key)
        
        if not prompt_template:
            return {"subject": "Error", "body": "Legacy prompt not found."}

        # Simple formatting for legacy
        formatted_enrichment = "\n".join([f"{k}: {v}" for k, v in enrichment_data.items() if v])
        
        prompt = prompt_template.format(
            first_name=lead_data.get("first_name", "there"),
            company=lead_data.get("company", ""),
        )
        
        result = self._call_llm(prompt)
        
        # Obsessive Content Audit
        self.logger.info(f"✍️  [CONTENT GEN] Generated copy for {lead_data.get('email')}")
        self.logger.info(f"   Subject: {result['subject']}")
        body_preview = result['body'].replace('\n', ' ')[:100] + "..."
        self.logger.info(f"   Body Preview: {body_preview}")
        
        return result

    def _call_llm(self, prompt: str, system_prompt: str = None) -> dict:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.4
            )
            return self._parse_response(response.choices[0].message.content)
        except Exception as e:
            self.logger.error(f"OpenAI Error: {e}")
            return {"subject": "Error", "body": str(e)}

    def _parse_response(self, content: str) -> dict:
        """Robustly parse LLM response, handling common formatting variations."""
        lines = [line.strip() for line in content.strip().split("\n") if line.strip()]
        subject = ""
        body_lines = []
        
        # 1. Attempt to find Subject
        for i, line in enumerate(lines):
            clean = line.replace("**", "").replace("#", "").strip()
            if clean.upper().startswith("SUBJECT:"):
                subject = clean.split(":", 1)[1].strip()
                # Remove subject line from body consideration
                continue
            
            # If we don't have a subject yet and this looks like a subject line (short, no punctuation)
            if not subject and i == 0 and len(clean) < 100:
                subject = clean
                continue
            
            # 2. Extract Body (everything else that isn't a "BODY:" header)
            if clean.upper().startswith("BODY:"):
                remaining = clean.split(":", 1)[1].strip()
                if remaining: body_lines.append(remaining)
            else:
                body_lines.append(line)
        
        # Final fallback if subject is still empty
        if not subject and body_lines:
            subject = "Checking in" # Safe fallback
            
        return {
            "subject": subject or "Quick question",
            "body": "\n".join(body_lines).strip()
        }
