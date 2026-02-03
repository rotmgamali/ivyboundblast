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

# Add project root to path to allow imports from sibling directories
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from logger_util import get_logger
load_dotenv()
logger = get_logger("EMAIL_GENERATOR")

# Try to import the scraper, fallback if missing
try:
    # First attempt: Root-relative import (Standard for our Docker setup)
    import automation_scrapers.school_scraper as school_scraper
    scrape_website_text = school_scraper.scrape_website_text
    logger.info("✓ Successfully imported school_scraper")
except ImportError as e:
    try:
        # Second attempt: Direct import (if path already adjusted)
        from automation_scrapers.school_scraper import scrape_website_text
        logger.info("✓ Successfully imported school_scraper via fallback")
    except ImportError:
        logging.warning(f"⚠️ Could not import school_scraper: {e}")
        logging.warning(f"🔍 sys.path currently includes: {sys.path[:3]}...")
        scrape_website_text = None

class EmailGenerator:
    """
    Generates hyper-personalized email content using OpenAI + Live Website Scraping.
    Uses 'Archetypes' to select the correct template folder (e.g. /principal).
    """

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

    LEGACY_PROMPTS = {}

    def __init__(self, client=None):
        self.client = client or OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.templates_dir = BASE_DIR / "templates"

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
        - If 'school', use the new Archetype + Scraper logic.
        - Otherwise, use legacy dictionary prompts.
        """
        if campaign_type == "school":
            return self._generate_school_email(sequence_number, lead_data, enrichment_data, sender_email)
        else:
            return self._generate_legacy_email(campaign_type, sequence_number, lead_data, enrichment_data)

    def _generate_school_email(self, sequence_number: int, lead_data: dict, enrichment_data: dict, sender_email: str = None) -> dict:
        """
        1. Identify Archetype (Role).
        2. Load Template (file).
        3. Scrape Website (if not already cached).
        4. Generate Email via LLM.
        """
        role = (lead_data.get("role") or "").lower()
        archetype = self._get_archetype(role)
        logger.info(f"🎯 [GEN] Archetype: {archetype} (detected from role: '{role}')")
        
        # Load Template
        template_content = self._load_template_file(archetype, sequence_number)
        
        # Fallback to general if not found and archetype isn't already general
        if not template_content and archetype != "general":
            logger.info(f"ℹ️ Template for {archetype}/{sequence_number} not found. Falling back to general.")
            template_content = self._load_template_file("general", sequence_number)
            
        if not template_content:
            logger.error(f"❌ Template missing for {archetype}/{sequence_number} and fallback general failed.")
            return {"subject": "Quick question", "body": "I'd love to connect regarding SAT/ACT prep at your school."}

        # Website Scraping
        website_content = enrichment_data.get("website_content", "")
        url = lead_data.get("domain") or lead_data.get("website")

        if not website_content and url and scrape_website_text:
            logger.info(f"🌍 [SCRAPE] Attempting to scrape: {url}...")
            try:
                if not url.startswith("http"):
                    url = "https://" + url
                website_content = scrape_website_text(url)
                if website_content and len(website_content) > 100:
                    logger.info(f"✅ [SCRAPE SUCCESS] Found {len(website_content)} characters for personalization.")
                else:
                    logger.warning(f"⚠️ [SCRAPE WEAK] Only found {len(website_content) if website_content else 0} chars. Personalization may be generic.")
            except Exception as e:
                logger.error(f"❌ [SCRAPE ERROR] Failed for {url}: {e}")
                website_content = "No website content available."
        elif not url:
            logger.warning(f"⚠️ [SCRAPE SKIP] No 'domain' or 'website' found in lead data for {lead_data.get('email')}.")
        
        # Build Prompts (System + User)
        system_prompt, user_prompt = self._prepare_school_prompts(
            template_content, lead_data, website_content, sequence_number, sender_email
        )
        
        return self._call_llm(user_prompt, system_prompt)

    def _get_archetype(self, role: str) -> str:
        """Map job title to archetype folder name."""
        for key, keywords in self.ARCHETYPES.items():
            if any(k in role for k in keywords):
                return key
        return "general"  # Default

    def _sanitize_name(self, name: str, lead_data: dict) -> str:
        """Sanitize first name to avoid 'Hi Harvest' or 'Hi Info'."""
        if not name: return ""
        name = name.strip()
        lower_name = name.lower()
        
        # Blocklist
        blocklist = ["info", "admin", "office", "contact", "admissions", "principal", "head", "school"]
        if lower_name in blocklist:
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

    def _load_template_file(self, archetype: str, sequence_number: int) -> Optional[str]:
        """Read template file from disk (e.g. templates/school/principal/email_1.txt)."""
        # Map sequence number to file name (email_1.txt)
        filename = f"email_{sequence_number}.txt"
        path = self.templates_dir / "school" / archetype / filename
        
        logger.debug(f"🔍 [PATH CHECK] Looking for template at: {path}")
        
        if path.exists():
            return path.read_text(encoding="utf-8")
        
        # Diagnostic: List files to see what's actually there
        try:
            if self.templates_dir.exists():
                contents = os.listdir(self.templates_dir)
                logger.debug(f"📁 [DIR LIST] Content of {self.templates_dir}: {contents}")
            else:
                logger.error(f"🚨 [DIR MISSING] Template directory NOT FOUND at {self.templates_dir}")
        except Exception as e:
            logger.debug(f"🔍 [DIR ERROR] Could not list directory: {e}")
            
        return None

    def _prepare_school_prompts(self, template_content: str, lead_data: dict, website_content: str, sequence_number: int, sender_email: str) -> tuple:
        """
        Constructs (system_message, user_message) for the LLM.
        Performs Python-side string substitution to guarantee greeting correctness.
        """
        
        # --- 1. Calculate Variables (Identity & Recipient) ---
        
        # Name & Greeting Logic
        raw_name = lead_data.get("first_name", "")
        sanitized = self._sanitize_name(raw_name, lead_data)
        
        if sanitized:
            first_name = sanitized
            # Religious Titles
            role = lead_data.get("role", "").lower()
            religious_titles = {"pastor": "Pastor", "reverend": "Reverend", "rev.": "Reverend", "father": "Father", "rabbi": "Rabbi"}
            for keyword, title in religious_titles.items():
                if keyword in role and title.lower() not in first_name.lower():
                    first_name = f"{title} {first_name}"
                    break
            greeting_line = f"Hi {first_name},"
        else:
            # Fallback to Time-Based
            greeting_line = f"{self._get_time_greeting()},"
            first_name = "School Leader" # Default for prompt context
            
        # Sender Logic
        sender_name = "Andrew"
        if sender_email:
            if "mark" in sender_email.lower(): sender_name = "Mark Greenstein"
            elif "genelle" in sender_email.lower(): sender_name = "Genelle"
        
        # --- 2. Python-Side Template Substitution (The Fix) ---
        # We replace the greeting placeholder in the code, so the LLM just sees text.
        # Handle variations of the tag
        draft_body = template_content
        for tag in ["Hi {{first_name}}", "Hi {{first_name}},", "{{first_name}}"]:
             draft_body = draft_body.replace(tag, greeting_line)
             
        # Double check: ensure the greeting is at the top if replacement failed (e.g. template diff)
        # But for now, assume template compliance. 
        
        # School/Location Context
        school_name = lead_data.get("school_name", "your school")
        city = lead_data.get("city", "")
        state = lead_data.get("state", "")
        location_txt = f"{city}, {state}" if city and state else ""
        
        # --- 3. System Prompt (Identity & Behavior) ---
        system_prompt = f"""You are {sender_name}, a helpful consultant for private schools.
        
STYLE GUIDE:
- Tone: Human, warm, brief. No "marketing" fluff. Lowercase aesthetic preferred.
- formatting: Standard email. No markdown headers (like **Subject**).
- Absolute Rules:
  1. NEVER invent facts. If research is missing, be generic but warm.
  2. DO NOT change the starting greeting sent in the draft.
  3. DO NOT add a second greeting (e.g. "Good morning... Good morning").
"""

        # --- 4. User Prompt (The Task) ---
        user_prompt = f"""Here is a DRAFT email I want to send to {first_name} ({lead_data.get('role')}) at {school_name}.

DRAFT EMAIL:
'''
{draft_body}
'''

RESEARCH HIGHLIGHTS:
{website_content[:3000]}

TASK:
Rewrite the draft to make it feel personal.
- If possible, gently weave in 1 specific detail from the RESEARCH HIGHLIGHTS (a program, mission, or city reference).
- Keep the greeting "{greeting_line}" EXACTLY as is.
- Sign off as {sender_name}.
- Output in this format:
SUBJECT: [Subject]
BODY: [Body]
"""
        return system_prompt, user_prompt

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
        logger.info(f"✍️  [CONTENT GEN] Generated copy for {lead_data.get('email')}")
        logger.info(f"   Subject: {result['subject']}")
        body_preview = result['body'].replace('\n', ' ')[:100] + "..."
        logger.info(f"   Body Preview: {body_preview}")
        
        return result

    def _call_llm(self, prompt: str, system_prompt: str = None) -> dict:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7
            )
            return self._parse_response(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"OpenAI Error: {e}")
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
