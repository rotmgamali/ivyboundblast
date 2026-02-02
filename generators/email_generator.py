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

# Try to import the scraper, fallback if missing
try:
    # First attempt: Root-relative import (Standard for our Docker setup)
    import scrapers.school_scraper as school_scraper
    scrape_website_text = school_scraper.scrape_website_text
    logger.info("✓ Successfully imported school_scraper")
except ImportError as e:
    try:
        # Second attempt: Direct import (if path already adjusted)
        from scrapers.school_scraper import scrape_website_text
        logger.info("✓ Successfully imported school_scraper via fallback")
    except ImportError:
        logging.warning(f"⚠️ Could not import school_scraper: {e}")
        logging.warning(f"🔍 sys.path currently includes: {sys.path[:3]}...")
        scrape_website_text = None

from logger_util import get_logger

load_dotenv()
logger = get_logger("EMAIL_GENERATOR")

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
        enrichment_data: dict
    ) -> dict:
        """
        Routing method:
        - If 'school', use the new Archetype + Scraper logic.
        - Otherwise, use legacy dictionary prompts.
        """
        if campaign_type == "school":
            return self._generate_school_email(sequence_number, lead_data, enrichment_data)
        else:
            return self._generate_legacy_email(campaign_type, sequence_number, lead_data, enrichment_data)

    def _generate_school_email(self, sequence_number: int, lead_data: dict, enrichment_data: dict) -> dict:
        """
        1. Identify Archetype (Role).
        2. Load Template (file).
        3. Scrape Website (if not already cached).
        4. Generate Email via LLM.
        """
        role = (lead_data.get("role") or "").lower()
        archetype = self._get_archetype(role)
        
        # Load Template
        template_content = self._load_template_file(archetype, sequence_number)
        if not template_content:
            logger.warning(f"Template not found for {archetype}/{sequence_number}. Using general.")
            template_content = self._load_template_file("general", sequence_number)
            
        if not template_content:
            return {"subject": "Error", "body": "Template missing."}

        # Website Scraping
        website_content = enrichment_data.get("website_content", "")
        url = lead_data.get("domain") or lead_data.get("website")

        if not website_content and url and scrape_website_text:
            logger.info(f"🌍 Scraping {url} for personalization...")
            try:
                if not url.startswith("http"):
                    url = "https://" + url
                website_content = scrape_website_text(url)
                logger.debug(f"🔍 Scrape summary for {url}: {len(website_content)} characters found.")
            except Exception as e:
                logger.error(f"❌ Scraping failed for {url}: {e}")
                website_content = "No website content available."
        
        # Build Prompt
        prompt = self._get_school_prompt(template_content, lead_data, website_content, sequence_number)
        
        return self._call_llm(prompt)

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
            # If name is just the first word of school (e.g. "Harvest" from "Harvest Academy")
            school_parts = school_name.split()
            if school_parts and lower_name == school_parts[0]:
                return ""
            # If name matches the school name exactly
            if lower_name == school_name:
                return ""
                
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
        
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def _get_school_prompt(self, template_content: str, lead_data: dict, website_content: str, sequence_number: int = 1) -> str:
        """Construct the LLM prompt for school emails with human-first personalization."""
        
        # Intelligent Name Sanitization
        raw_name = lead_data.get("first_name", "")
        school_name = lead_data.get("school_name", "your school")
        city = lead_data.get("city", "")
        state = lead_data.get("state", "")
        role = lead_data.get("role", "")
        subtypes = lead_data.get("subtypes", "")
        description = lead_data.get("description", "")
        
        sanitized = self._sanitize_name(raw_name, lead_data)
        
        # Fallback Logic
        if sanitized:
            first_name = sanitized
            
            # Religious Title Logic: Check if we should add a title
            # Keywords to check in ROLE
            religious_titles = {
                "pastor": "Pastor",
                "reverend": "Reverend", 
                "rev.": "Reverend",
                "father": "Father",
                "fr.": "Father",
                "rabbi": "Rabbi",
                "sister": "Sister",
                "brother": "Brother"
            }
            role_lower = str(role).lower()
            
            for keyword, title in religious_titles.items():
                if keyword in role_lower:
                    # Avoid double titling if name already has it (e.g. "Pastor Andrew")
                    if title.lower() not in first_name.lower():
                        first_name = f"{title} {first_name}"
                    break
        else:
            # STRICT FALLBACK RULE:
            # If no valid name, ALWAYS use Time-Based Greeting.
            # No "Admissions Team", No "Hi Team".
            first_name = self._get_time_greeting()
        
        # Determine Greeting vs Name
        # If we have a time greeting (starts with Good), use it directly.
        if first_name.startswith("Good "):
            greeting_line = f"{first_name},"
            template_instruction = f"IMPORTANT: Start the email with '{greeting_line}' exactly. Do NOT write 'Hi {first_name}'."
        else:
            greeting_line = f"Hi {first_name},"
            template_instruction = ""
            
        # Determine sender based on archetype/strategy
        
        # Determine sender based on archetype/strategy
        sender_name = "Andrew"
        if any(keyword in str(role).lower() for keyword in ["head of school", "headmaster", "president", "superintendent", "business", "finance", "cfo"]):
            sender_name = "Mark Greenstein"
        elif any(keyword in str(role).lower() for keyword in ["dean", "academic", "curriculum", "instruction"]):
            sender_name = "Genelle"
            
        # Determine email purpose based on sequence
        if sequence_number == 1:
            email_purpose = "WARM INTRODUCTION: Build curiosity. Show you did your research on their school and city. No hard sell."
        else:
            email_purpose = "VALUE FOLLOW-UP: Build on the previous intro. Use specific stats and a soft call to action."
        
        # Build location context
        location_context = ""
        if city and state:
            location_context = f"The school is in {city}, {state}. Weave this in naturally (e.g., 'I know schools in the {city} area are busy...')."
            
        return f"""You are {sender_name}, writing a personalized email to {first_name} ({role}) at {school_name}.

GOAL: {email_purpose}

TEMPLATE (Use the flow and core message, but make the wording feel human and natural):
---
{template_content}
---

INSTRUCTION: {template_instruction}
If the template says "Hi {{first_name}}", replace it with "{greeting_line}".

VERIFIED DATA (ONLY use these facts):
- Recipient: {first_name}
- School: {school_name}
- Role: {role}
- Location: {city}, {state}
- Info: {subtypes} | {description[:300] if description else "N/A"}
---

SCRAPED WEBSITE CONTENT (FIND 1-2 SPECIFIC DETAILS TO HOOK INTO):
---
{website_content[:4000] if website_content else "No website content available."}
---

STRICT PERSONALIZATION RULES:
1. **The 'Five-Minute Rule'**: Write this as if you actually spent 5 minutes on their website. 
2. **The Hook**: Find a SPECIFIC program, achievement, or mission phrase from the SCRAPED CONTENT. Weave it into the first paragraph naturally. (e.g., "I saw your focus on global citizenship..." or "I noticed your recent success in...").
3. **Location Context**: Mention their city/state ({{city}}) naturally and warmly.
4. **Role Mindset**:
   - Pastoral → mission, community, student growth.
   - Head/Principal → parent satisfaction, outcomes, tuition value.
   - Athletics → student-athlete balance, scholarships.
   - Admissions → enrollment value, recruitment advantage.
5. **No Hallucination**: NEVER invent a fact. If the scrape is empty, don't fake a detail.
6. **Tone**: Human-first. Brief. No "corporate speak." No "I am writing to..." 
7. **Sign off**: Match the sender name {sender_name}.

OUTPUT FORMAT:
SUBJECT: [A subject line that gets opened]
BODY: [The email body]
"""

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

    def _call_llm(self, prompt: str) -> dict:
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
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
