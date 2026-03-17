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
        if campaign_type in ["school", "b2b"]:
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
        
        # --- 1. Identify Archetype ---
        role = (lead_data.get("role") or "").lower()
        archetype = self._get_archetype(role)
        _logger.debug(f"🎯 [GEN] {campaign_type.upper()} Archetype: {archetype} (detected from role: '{role}')")
        
        # --- 2. Load Template ---
        template_content = self._load_template_file(campaign_type, archetype, sequence_number)
        
        # Fallback to general if not found and archetype isn't already general
        if not template_content and archetype != "general":
            _logger.debug(f"ℹ️ Template for {archetype}/{sequence_number} not found. Falling back to general.")
            template_content = self._load_template_file(campaign_type, "general", sequence_number)
            
        if not template_content:
            _logger.error(f"❌ Template missing for {campaign_type}/{archetype}/{sequence_number} and fallback general failed.")
            return {"subject": "Quick question", "body": "I'd love to connect regarding your current operations."}

        # --- 3. Scrape Website ---
        website_content = enrichment_data.get("website_content", "")
        
        if not website_content and url:
            # SANITY CHECK: Ensure we aren't scraping Google Maps
            if "google.com" in url.lower() or "goo.gl" in url.lower():
                self.logger.warning(f"⚠️ Skipping scrape for Google URL: {url}")
                website_content = "Scraper skipped for Google URL."
            else:
                try:
                    if not url.startswith("http"):
                        url = "https://" + url
                    
                    # Try external scrapers first
                    if campaign_type == "b2b" and b2b_scraper:
                        website_content = b2b_scraper.scrape_b2b_text(url)
                    elif school_scraper:
                        website_content = school_scraper.scrape_website_text(url)
                    else:
                        # FALLBACK: Built-in robust scraper
                        website_content = self._fallback_scrape(url)

                    if website_content and len(website_content) > 100:
                        self.logger.debug(f"✅ [SCRAPE SUCCESS] Found {len(website_content)} characters for personalization.")
                    else:
                        self.logger.warning(f"⚠️ [SCRAPE WEAK] Only found {len(website_content) if website_content else 0} chars.")
                except Exception as e:
                    self.logger.error(f"❌ [SCRAPE ERROR] Failed for {url}: {e}")
                    website_content = "No website content available."

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
            campaign_type, template_content, lead_data, website_content, sequence_number, sender_email, custom_context
        )
        
        # Call LLM for Body & Subject
        llm_result = self._call_llm(user_prompt, system_prompt)
        
        self.logger.info(f"✍️ [LLM RESULT] Subject: {llm_result.get('subject')}")
        self.logger.info(f"✍️ [LLM RESULT] Body Snippet: {llm_result.get('body')[:100]}...")
        
        # --- ENVELOPE REASSEMBLY ---
        clean_body = self._strip_hallucinations(llm_result['body'], envelope['greeting'], envelope['sign_off'])
        
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

    def _fallback_scrape(self, url: str) -> str:
        """Internal lightweight scraper for website text."""
        import requests
        from bs4 import BeautifulSoup
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=15, verify=False)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Remove script/style
                for s in soup(["script", "style"]):
                    s.decompose()
                text = soup.get_text(separator=' ')
                # Clean whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                return text[:5000]
        except Exception as e:
            self.logger.error(f"Fallback scrape failed: {e}")
        return ""

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
        path = self.templates_dir / campaign_type / archetype / filename
        
        _logger.debug(f"🔍 [PATH CHECK] Looking for template at: {path}")
        
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

    def _prepare_templated_prompts(self, campaign_type: str, template_content: str, lead_data: dict, website_content: str, sequence_number: int, sender_email: str, custom_context: str = "") -> tuple:
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
        sanitized = self._sanitize_name(raw_name, lead_data)
        role = lead_data.get("role", "").strip()
        school_name = lead_data.get("school_name") or lead_data.get("company_name") or "your school"
        
        if sanitized:
            first_name = sanitized
            # Religious Titles
            role_lower = role.lower()
            religious_titles = {"pastor": "Pastor", "reverend": "Reverend", "rev.": "Reverend", "father": "Father", "rabbi": "Rabbi"}
            for keyword, title in religious_titles.items():
                if keyword in role_lower and title.lower() not in first_name.lower():
                    first_name = f"{title} {first_name}"
                    break
            greeting_line = f"Hi {first_name},"
        elif role and len(role) > 2 and role.lower() not in ["high school", "middle school", "elementary school", "pk-12"]:
            # Fallback to Role-based (e.g. Hi Principal,)
            first_name = role.title()
            greeting_line = f"Hi {first_name},"
        elif school_name and school_name.lower() != "your school":
            # Fallback to School-based Team
            greeting_line = f"To the {school_name} Team,"
            first_name = "Team"
        else:
            # Absolute fallback
            greeting_line = "Hi,"
            first_name = "School Leader"
            
        # Sender Logic
        sender_name = "Andrew"
        if sender_email:
            if "mark" in sender_email.lower(): sender_name = "Mark Greenstein"
            elif "genelle" in sender_email.lower(): sender_name = "Genelle"
        
        
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
        # Define the deterministic shell
        sign_off_block = f"Best,\n{sender_name}"
        envelope = {
            "greeting": greeting_line,
            "sign_off": sign_off_block,
            "subject": template_subject # Default, AI will override if instructed
        }
        
        # --- 5. System Prompt (Constraint) ---
        system_prompt = f"""You are {sender_name}, a helpful education consultant.
        
STYLE GUIDE:
- Tone: Human, warm, brief, and professional. NO CORPORATE JARGON.
- Formatting: Use paragraphs only. Spaced out.
- Absolute Rules:
  1. DO NOT include a greeting (e.g. "Hi...").
  2. DO NOT include a sign-off (e.g. "Best, Mark").
  3. OUTPUT ONLY the Subject and the Body paragraphs.

- IF PUBLIC: Focus on district alignment, budget efficiency, and test scores.
- IF PRIVATE: Focus on enrollment, prestige, and college matriculation.

PLACEHOLDER POLICY:
- NEVER use brackets or parentheses for unknown data.
- If unsure, OMIT or use a natural, generic phrase.
"""

        # --- 6. User Prompt (Body & Subject Generation) ---
        user_prompt = f"""You are a local parent/neighbor writing a 1-to-1 email to {first_name} at "{school_name}".

RESEARCH HIGHLIGHTS (Live Web Scrape):
{website_content[:4500]}

DRAFT CONTENT:
'''
{clean_draft}
'''

LEAD CONTEXT:
{custom_context}

TASK:
1. SUBJECT LINE: Write a 2-4 word "Insider" subject line.
   - It must look like a casual email from a local.
   - EXAMPLES of what I want: "Go [Mascot Name]!", "[Neighborhood Name] families", "Question about [Local Event]", "[City Nickname] student support", "[Specific Program Name] question".
   - DO NOT use: "Question", "Resources", "Test Prep", "Introduction", or the school's full formal name.
   - If you find a mascot or a specific local street/park in the research, use it.

2. BODY: Rewrite the DRAFT CONTENT to be deeply personalized. 
   - Reference a specific detail found in the RESEARCH (e.g., a specific teacher's award, a unique elective, a recent social media post mentioned on the site).
   - The tone must be "I saw this on your site and it made me think of..." rather than "I am a consultant...".

3. CONSTRAINTS:
   - NO GREETINGS or SIGN-OFFS.
   - NO PLACEHOLDERS.
   - KEEP IT UNDER 75 WORDS.

Output format:
SUBJECT: [Insider Subject]

BODY: [Paragraph 1]

[Paragraph 2]
"""
        return system_prompt, user_prompt, envelope

    def _strip_hallucinations(self, body_text: str, greeting: str, sign_off: str) -> str:
        """Failsafe: If AI wrote 'Hi Andrew,' or 'Best, Name' anyway, remove it."""
        lines = body_text.split("\n")
        
        # 1. Strip Leading Greeting (be very thorough)
        greeting_markers = ["hi", "dear", "good morning", "good afternoon", "good evening", "hello", "to the", "attention"]
        if lines and any(g.lower() in lines[0].lower() for g in greeting_markers):
            # Check if it looks like a greeting (short, ends in comma/colon)
            first_line = lines[0].strip()
            if "," in first_line or ":" in first_line or len(first_line) < 40:
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
        
        # 3. Strip Bracketed/Parenthetical Hallucinations (e.g. [City], (Name))
        # This regex catches: [Text], (text), (Text), [City], etc.
        # It replaces them with a generic community/organization reference if possible, 
        # or just removes them.
        body = re.sub(r'\[[^\]]+\]', 'your community', body)
        body = re.sub(r'\([^\)]+\)', 'your community', body)
        
        # Cleanup double spaces or weird punctuation left behind
        body = body.replace('your community your community', 'your community')
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
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7
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
