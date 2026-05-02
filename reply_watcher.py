import os
import json
import logging
import time
import argparse
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Add project root path
import sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "mailreef_automation"))
sys.path.insert(0, BASE_DIR)

from mailreef_automation.mailreef_client import MailreefClient
import mailreef_automation.automation_config as automation_config
from sheets_integration import GoogleSheetsClient
from generators.email_generator import EmailGenerator
import lock_util

# Configuration
MAILREEF_API_KEY = os.getenv("MAILREEF_API_KEY")
if not MAILREEF_API_KEY:
    load_dotenv()
    MAILREEF_API_KEY = os.getenv("MAILREEF_API_KEY")

STATE_FILE = "mailreef_automation/logs/reply_watcher_state.json"
CHECK_INTERVAL_MINUTES = 5

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
from logger_util import get_logger

# We need to defer logger creation until we know the profile... 
# OR just create a generic one and re-init later?
# ReplyWatcher class handles profile. Let's let the class handle logging?
# But `logger` is global. 
# Let's remove the global logger init or make it generic.
logger = get_logger("REPLY_WATCHER", "automation.log") # Default initially


class ReplyWatcher:
    def __init__(self, mailreef_client=None, config=None, profile_name="IVYBOUND"):
        self.profile_name = profile_name.upper()
        self.config = config or automation_config
        self.mailreef = mailreef_client or MailreefClient(api_key=MAILREEF_API_KEY)
        self.lock_name = f'watcher_{self.profile_name.lower()}'
        
        # Ensure only one instance runs per profile
        lock_util.ensure_singleton(self.lock_name)
        
        self.state_file = f"mailreef_automation/logs/reply_watcher_{self.profile_name.lower()}_state.json"
        
        self.mailreef = MailreefClient(api_key=MAILREEF_API_KEY)
        
        profile_config = automation_config.CAMPAIGN_PROFILES[self.profile_name]
        
        # --- LOGGING ISOLATION ---
        # Re-bind the global logger to the profile-specific file
        # and remove the default 'automation.log' handler to prevent leakage.
        global logger
        log_file = profile_config.get("log_file", "automation.log")
        logger = get_logger("REPLY_WATCHER", log_file)
        
        # Clean up default handler if we switched to a specific one
        # (This ensures "strategy_b.log" doesn't also get written to "automation.log")
        if log_file != "automation.log":
            for h in logger.handlers[:]:
                if isinstance(h, logging.FileHandler) and "automation.log" in h.baseFilename:
                    logger.removeHandler(h)
                    
        self.sheets_client = GoogleSheetsClient(
            input_sheet_name=profile_config["input_sheet"],
            input_worksheet_name=profile_config.get("input_worksheet"),
            replies_sheet_name=profile_config["replies_sheet"],
            replies_sheet_id=profile_config.get("replies_sheet_id"),
            replies_worksheet_name=getattr(self.config, "ACTIVE_REPLIES_WORKSHEET", None)
        )
        self.sheets_client.setup_sheets() # Ensure sheet1 is available
        self.generator = EmailGenerator() # Used for sentiment analysis
        
        # --- CAMPAIGN INBOX ISOLATION ---
        self.campaign_inboxes = set()
        self._load_campaign_inboxes()
        
        # --- LEAD-FIRST FILTERING ---
        # Cache all lead emails to ensure we NEVER filter out a real reply
        self.lead_emails = set()
        self.lead_domains = set()
        self.generic_domains = {
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com', 
            'aol.com', 'msn.com', 'live.com', 'protonmail.com', 'me.com', 'comcast.net'
        }
        self._load_lead_emails()

    def _load_campaign_inboxes(self):
        """Identifies which inboxes belong to this specific campaign profile."""
        try:
            profile_config = automation_config.CAMPAIGN_PROFILES[self.profile_name]
            indices = profile_config.get("inbox_indices")
            
            if not indices:
                logger.warning(f"⚠️ [WATCHER] No inbox indices defined for {self.profile_name}. Monitoring ALL inboxes (Risk of leakage).")
                return

            all_inboxes = self.mailreef.get_inboxes()
            # Sort by ID to ensure consistent indexing with Scheduler
            all_inboxes.sort(key=lambda x: x['id'])
            
            start, end = indices
            campaign_list = all_inboxes[start:end]
            
            for f in campaign_list:
                # Mailreef API returns the email address in the 'id' field
                email = f.get("id", "").lower().strip()
                if email:
                    self.campaign_inboxes.add(email)
            
            logger.info(f"📋 [WATCHER] Monitoring {len(self.campaign_inboxes)} dedicated inboxes for {self.profile_name}.")
            # logger.debug(f"Monitored emails: {self.campaign_inboxes}")
            
        except Exception as e:
            logger.error(f"❌ [WATCHER] Failed to load campaign inboxes: {e}")

    def _load_lead_emails(self):
        """Loads all lead emails and domains from the current profile's input sheet/tab.

        Uses the profile's configured input_worksheet (e.g. "Bahamas Retreat - Leads"
        for BAHAMAS_RETREAT) instead of always reading sheet1, which previously
        caused the Bahamas reply watcher to load Ivybound leads and miss every
        real Bahamas reply via the lead-first filter.
        """
        try:
            logger.info(f"📋 [WATCHER] Loading lead list for {self.profile_name} to guarantee no missed replies...")
            ws = self.sheets_client._input_worksheet()
            records = ws.get_all_records()
            tab_label = self.sheets_client.input_worksheet_name or "sheet1"
            for r in records:
                email = str(r.get('email', '')).lower().strip()
                if email:
                    self.lead_emails.add(email)
                    if '@' in email:
                        domain = email.split('@')[-1]
                        if domain not in self.generic_domains:
                            self.lead_domains.add(domain)
            logger.info(
                f"✅ [WATCHER] Loaded {len(self.lead_emails)} lead emails and "
                f"{len(self.lead_domains)} lead domains from tab {tab_label!r}."
            )
        except Exception as e:
            logger.error(f"❌ [WATCHER] Failed to load lead list: {e}")
        
    def load_state(self) -> dict:
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                if "processed_msg_ids" not in state:
                    state["processed_msg_ids"] = []
                return state
        return {"last_check": (datetime.now() - timedelta(hours=24)).isoformat(), "processed_msg_ids": []}

    def save_state(self, state: dict):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(state, f)

    def is_warmup(self, from_email: str, subject: str, msg: dict = None) -> bool:
        """
        Differentiate between Ivy Bound system emails and Mailreef warmup service.
        1. Lead-First: If the sender is in our lead list, it is NEVER warmup.
        2. Subject check: Normal filtering logic.
        3. Body check: Specific warming tags.
        """
        if not from_email:
            return True
            
        # 1. LEAD-FIRST CHECK (Exact Email)
        email_clean = from_email.lower().strip()
        if email_clean in self.lead_emails:
            logger.info(f"📬 [REPLY] Exact match found for lead: {email_clean}")
            return False

        # 1b. LEAD-DOMAIN CHECK (Exclude generic domains)
        if '@' in email_clean:
            domain = email_clean.split('@')[-1]
            if domain in self.lead_domains:
                logger.info(f"📬 [REPLY] Domain match found for lead: {email_clean} (@{domain})")
                return False

        subj_lower = subject.lower() if subject else ""
        
        # 0. SUBJECT-MATCH PRIORITY (The "Inverse" filter)
        # If the subject contains one of OUR phrases, it's almost certainly a real reply.
        # We bypass all bot filtering in this case.
        profile_config = self.config.CAMPAIGN_PROFILES.get(self.profile_name, {})
        known_patterns = profile_config.get("subject_patterns", [])
        for p in known_patterns:
            if p.lower() in subj_lower:
                logger.info(f"🎯 [MATCH] Confirmed real reply via subject match: '{p}'")
                return False

        # 1. Subject Warmup patterns
        warmup_patterns = [
            "bug fixes", "software training", "expense reports",
            "sales report", "performance reviews",
            "volunteer day", "vendor negotiations", "health benefits",
            "team building", "intern welcome",
            "strategic planning", "remote work", "client meeting",
            "project update", "policy reminder", "office move",
            "company picnic", "birthday celebration", "quarterly goals",
            "tax compliance", "w-8ben", "documentation notice", "productivity tips",
            "celebration planning", "management system update", "achievement recognition",
            "maintenance notice", "hr policies", "marketing strategies",
            "training session", "retreat planning", "improvement suggestions",
            "challenge discussion", "publication discussion", "contact person",
            "new hire", "it support", "leave request", "w-8", "tax forms",
            "security update", "account action", "mandatory account", 
            "office recycling", "employee satisfaction", "project timeline",
            "inventory check", "travel plans", "milestone achievement"
        ]
        
        for pattern in warmup_patterns:
            if pattern in subj_lower:
                logger.debug(f"🗑️ [FILTER] Filtered as warmup (Subject: {pattern}): {from_email}")
                return True

        # 2. Body/Snippet Warmup tags (Unique hyphenated words)
        if msg:
            content = f"{msg.get('snippet_preview', '')} {msg.get('body_text', '')}".lower()
            body_tags = [
                "other-", "stock-globe", "blank-order", "point-where", 
                "noise-chest", "occur-light", "basic-route", "queen-again",
                "wrong-broke", "other-them", "other-feedback", "event-pupil"
            ]
            for tag in body_tags:
                if tag in content:
                    logger.debug(f"🗑️ [FILTER] Filtered as warmup (Body Tag: {tag}): {from_email}")
                    return True
                
        # 3. DEFAULT TO FALSE: If we aren't sure, let it through.
        return False

    def get_inbox_replies(self, since: str) -> List[Dict]:
        """Fetch all inbound replies using the global scan endpoint."""
        replies = []
        try:
            # INCREASED ROBUSTNESS: Fetch top 3 pages (300 emails) 
            # to ensure high-volume warmup doesn't push real replies out of sight.
            for page in range(1, 4):
                logger.debug(f"Fetching global inbound page {page}...")
                result = self.mailreef.get_global_inbound(page=page, display=100)
                batch = result.get("data", [])
                if not batch:
                    break
                
                # Filter by date if since is provided
                if since:
                    try:
                        since_dt = datetime.fromisoformat(since)
                    except ValueError:
                        since_dt = datetime.now() - timedelta(hours=24)
                else:
                    since_dt = datetime.now() - timedelta(hours=24)

                for msg in batch:
                    from_email = str(msg.get("from_email", "")).lower().strip()
                    subject = msg.get("subject_line", "")
                    
                    ts = msg.get("ts")
                    # ts is unix timestamp
                    msg_dt = datetime.fromtimestamp(ts)
                    # Filter by date FIRST to prevent spamming logs with historical matches
                    if msg_dt <= since_dt:
                        continue
                        
                    # FILTER 1: Skip archived emails (Mailreef Routing Rules)
                    # If the user sets up an auto-archive rule for warming, we skip it here.
                    if msg.get("archived") is True:
                        logger.debug(f"⏭️ [SKIP] Email is archived by Mailreef routing: {subject}")
                        continue

                    # FILTER 2: Skip warming emails (but known leads always pass)
                    if self.is_warmup(from_email, subject, msg):
                        continue

                    # ========== LEAD-FIRST PRIORITY ==========
                    # If the sender is a known lead, ALWAYS accept the reply.
                    # Skip inbox partition and subject pattern checks entirely.
                    is_known_lead = from_email in self.lead_emails
                    if not is_known_lead and '@' in from_email:
                        sender_domain = from_email.split('@')[-1]
                        if sender_domain in self.lead_domains:
                            is_known_lead = True
                    
                    if is_known_lead:
                        logger.info(f"📬 [LEAD REPLY] Accepting reply from known lead: {from_email} — Subject: {subject}")
                    else:
                        # NON-LEAD: Apply inbox-partition + profile-aware subject filtering.
                        # Note: this path mostly catches replies from forwarded recipients
                        # ("a colleague replied") whose email isn't in our lead sheet.
                        #
                        # FILTER A: Inbox partition — must land in a campaign inbox.
                        to_email = msg.get("to")[0] if msg.get("to") else "unknown"
                        if self.campaign_inboxes and to_email.lower().strip() not in self.campaign_inboxes:
                            logger.debug(f"⏭️ [SKIP] Non-lead reply to {to_email} — not in {self.profile_name} partition")
                            continue

                        # FILTER B: Subject must match the profile's own subject_patterns
                        # OR (for school campaigns) one of the legacy free-text fragments.
                        profile_config = automation_config.CAMPAIGN_PROFILES[self.profile_name]
                        subject_patterns = profile_config.get("subject_patterns", [])
                        clean_subject = re.sub(r'^(Re|Fwd|RE|FWD):\s*', '', subject, flags=re.IGNORECASE).strip().lower()

                        # Treat profile subject_patterns as substring matches (not just startswith)
                        # so dynamic patterns like "Quick question about X" / "Retreats for Y"
                        # / "{{ company_name }}" all match. Strip template placeholders.
                        pattern_strs = [
                            re.sub(r"\{\{[^}]+\}\}", "", p).strip().lower()
                            for p in subject_patterns
                        ]
                        pattern_strs = [p for p in pattern_strs if len(p) >= 4]
                        matches_profile = any(p in clean_subject for p in pattern_strs)

                        # Legacy fragments (school-era) — kept for backward compat with
                        # IVYBOUND replies still arriving from older subject lines.
                        legacy_fragments = [
                            "quick question", "supporting families", "boosting enrollment",
                            "academic outcomes", "differentiation", "merit scholarship",
                            "college readiness", "student-athletes", "test prep",
                            "enhancing value", "families and college prep",
                        ]
                        matches_legacy = any(frag in clean_subject for frag in legacy_fragments)

                        # B2B / Bahamas-style heuristic: "retreat", "villa", "offsite",
                        # "team event", "private property" — natural-language matches
                        # to anything that looks like a hospitality/retreat reply.
                        b2b_fragments = [
                            "retreat", "villa", "offsite", "team event",
                            "private property", "bahamas", "executive offsite",
                        ]
                        matches_b2b = any(frag in clean_subject for frag in b2b_fragments)

                        if not (matches_profile or matches_legacy or matches_b2b):
                            logger.debug(f"⏭️ [SKIP] Non-lead subject didn't match profile/legacy/b2b fragments: {subject!r}")
                            continue

                    # Normalize keys for the rest of the script
                    msg["from_email"] = msg.get("from_email")
                    # 1. Try body_text (full), 2. Try body_html (stripped), 3. Snippet
                    body_text = msg.get("body_text")
                    if not body_text and msg.get("body_html"):
                        body_text = re.sub('<[^<]+?>', '', msg.get("body_html"))
                        
                    msg["body"] = body_text if body_text else msg.get("snippet_preview", "")
                    msg["subject"] = subject
                    msg["date"] = msg_dt.isoformat()
                    msg["msg_id"] = str(msg.get("id", ""))
                    # Extra context
                    msg["inbox_email"] = msg.get("to")[0] if msg.get("to") else "unknown"
                    
                    replies.append(msg)
                            
        except Exception as e:
            logger.error(f"Error in global reply fetch: {e}")
        
        return replies

    # Intents we route on. HOT/WARM/QUESTION get an AI-drafted response;
    # NEGATIVE drives suppression; OUT_OF_OFFICE/REFERRAL/UNCLEAR are logged
    # for human review without a draft.
    INTENT_LABELS = (
        "HOT_BOOK_CALL",     # explicit ask to schedule / "send me a calendar link"
        "WARM_INTERESTED",   # interested but not asking for a meeting yet
        "QUESTION",          # asking for pricing/details/clarification
        "OBJECTION_PRICE",   # cost / budget concern
        "OBJECTION_TIMING",  # not now / try later / busy season
        "REFERRAL",          # forwarding to a colleague or saying who to contact
        "OUT_OF_OFFICE",     # automatic OOO bounce
        "NEGATIVE",          # opt-out / unsubscribe / not interested
        "UNCLEAR",
    )
    DRAFT_INTENTS = {"HOT_BOOK_CALL", "WARM_INTERESTED", "QUESTION", "OBJECTION_PRICE", "OBJECTION_TIMING"}
    NEGATIVE_INTENTS = {"NEGATIVE"}

    def classify_intent(self, reply_text: str, lead_role: str = "") -> str:
        """Multi-class intent of a reply. Returns one of INTENT_LABELS."""
        text = (reply_text or "").strip()
        if not text:
            return "UNCLEAR"
        prompt = f"""Classify this email reply from a recipient of cold outreach.

Reply text:
\"\"\"{text[:1500]}\"\"\"

Recipient role: {lead_role or "unknown"}

Return ONE label, exactly as written, no other words:
- HOT_BOOK_CALL  — explicitly wants a meeting / call / demo / "send a calendar link" / "what time works"
- WARM_INTERESTED — positive signal but no concrete ask yet ("tell me more", "sounds interesting")
- QUESTION — asking for pricing, details, brochure, references, or clarification
- OBJECTION_PRICE — concerned about cost / budget / "we can't afford"
- OBJECTION_TIMING — not now / try later / "circle back next quarter" / busy season
- REFERRAL — forwarding to a colleague / "you should talk to X" / "contact Jane instead"
- OUT_OF_OFFICE — automatic out-of-office or vacation auto-reply
- NEGATIVE — wants to stop / unsubscribe / "remove me" / "not interested" (any polite phrasing counts)
- UNCLEAR — none of the above
"""
        try:
            response = self.generator.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10,
            )
            label = (response.choices[0].message.content or "").strip().upper()
            label = re.sub(r"[^A-Z_]", "", label.split()[0]) if label else ""
            return label if label in self.INTENT_LABELS else "UNCLEAR"
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return "UNCLEAR"

    def draft_reply_response(
        self,
        intent: str,
        reply_text: str,
        original_outbound: str,
        lead_context: dict,
        sender_identity: dict,
    ) -> str:
        """Draft a tailored response to a positive/question reply. Returns
        a string the user can paste into Mailreef. Never auto-sends."""
        if intent not in self.DRAFT_INTENTS:
            return ""

        first_name = (lead_context.get("first_name") or "").strip()
        role = (lead_context.get("role") or "").strip()
        school = (lead_context.get("school_name") or lead_context.get("company_name") or "").strip()
        sender_name = (sender_identity or {}).get("name") or "Andrew"
        sender_title = (sender_identity or {}).get("title") or "Ivybound Education Partners"

        intent_brief = {
            "HOT_BOOK_CALL": (
                "They want to schedule. Confirm a 15-min call this week or next, propose 2 specific time "
                "windows in their likely time zone (e.g. Tue 10:30 AM ET or Thu 2:00 PM ET), and offer a "
                "calendar link if they prefer. Keep it short."
            ),
            "WARM_INTERESTED": (
                "They're warm. Offer the lightest next step that still creates momentum — a 10-min intro call OR "
                "a 1-page overview, their pick. Don't oversell. Ask one qualifying question relevant to their role."
            ),
            "QUESTION": (
                "Answer their specific question(s) directly using ONLY facts from the original outbound below. "
                "If they asked for pricing, give the package(s) at face value. End by inviting a 15-min call or "
                "asking a clarifying question."
            ),
            "OBJECTION_PRICE": (
                "Acknowledge the budget concern, then briefly reframe value (ROI, the score guarantee or "
                "money-back terms from the offer), and offer a low-risk next step (intro call, no commitment)."
            ),
            "OBJECTION_TIMING": (
                "Acknowledge the timing, suggest a specific reconnect window (e.g. 'I'll circle back in 6 weeks'), "
                "and ask if there's any prep info you can send now so they're ready to evaluate then."
            ),
        }[intent]

        system = (
            f"You are {sender_name} from {sender_title}. You are responding to a real reply to your "
            "cold outreach. Voice: confident, peer-to-peer, never corporate. Short sentences. "
            "Tight paragraphs. NO greeting line, NO sign-off, NO placeholder brackets — output ONLY the "
            "body text. Do NOT invent statistics, dates, names, or details. Use ONLY the facts in the "
            "original outbound and the recipient's reply. If you can't personalize without inventing, "
            "stay generic but professional. 70-130 words."
        )
        user = f"""Intent: {intent}
Guidance: {intent_brief}

Recipient: {first_name or "(no first name)"}, role: {role or "(unknown)"}, organization: {school or "(unknown)"}.

YOUR ORIGINAL OUTBOUND (facts you may reference):
\"\"\"{(original_outbound or "")[:1800]}\"\"\"

THEIR REPLY (respond to this directly):
\"\"\"{(reply_text or "")[:1500]}\"\"\"

Write the body of your response. No greeting, no sign-off."""
        try:
            response = self.generator.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.4,
                max_tokens=400,
            )
            draft = (response.choices[0].message.content or "").strip()
            # Wrap with greeting + sign-off so the user can paste verbatim.
            greeting = f"Hi {first_name}," if first_name else "Hi,"
            sign_off = f"\n\nBest,\n{sender_name}\n{sender_title}"
            return f"{greeting}\n\n{draft}{sign_off}"
        except Exception as e:
            logger.error(f"Draft generation failed: {e}")
            return ""

    def analyze_sentiment(self, text: str) -> str:
        """Analyze reply sentiment. Explicitly catches opt-out language as negative."""

        # Load custom prompt if defined in profile
        profile_config = automation_config.CAMPAIGN_PROFILES[self.profile_name]
        prompt_file = profile_config.get("reply_prompt")

        if prompt_file and os.path.exists(os.path.join(BASE_DIR, prompt_file)):
            with open(os.path.join(BASE_DIR, prompt_file), 'r') as f:
                base_prompt = f.read()
            prompt = base_prompt.replace("{{ body }}", text)
        else:
            prompt = f"""Analyze this email reply from a school administrator who received cold outreach about SAT/ACT test prep.

Classify as:
- 'positive': Interested, wants to learn more, asks questions, proposes a meeting, forwards to a colleague
- 'negative': Not interested, asks to stop, asks to be removed, says "no thanks", angry, compliance/legal threat
- 'neutral': Out of office auto-reply, acknowledged but noncommittal, forwarded without comment

CRITICAL: If the person says ANY variant of "stop", "remove", "unsubscribe", "not interested", "don't contact", "take me off", "no thank you", "please don't", "do not email" — classify as 'negative' even if the tone is polite.

REPLY:
{text}

Return ONLY one word: positive, negative, or neutral."""

        try:
            response = self.generator.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10
            )
            return response.choices[0].message.content.strip().lower()
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return "neutral"

    def send_auto_reply(self, to_email: str, thread_id: str, inbox_id: str):
        """Sends the follow-up pitch (Email 2) as an auto-reply."""
        profile_config = automation_config.CAMPAIGN_PROFILES[self.profile_name]
        template_file = profile_config.get("auto_reply_template")
        
        if not template_file:
            logger.warning("No auto-reply template configured for this profile.")
            return

        # Construct full path to template
        # templates_dir is base, auto_reply_template is relative to it? 
        # Config says: "templates_dir": "templates/web4guru/accountants"
        # "auto_reply_template": "partner/email_2.txt"
        base_tpl_dir = profile_config.get("templates_dir", "templates")
        full_tpl_path = os.path.join(BASE_DIR, base_tpl_dir, template_file)
        
        if not os.path.exists(full_tpl_path):
             logger.error(f"Auto-reply template not found at {full_tpl_path}")
             return

        try:
            with open(full_tpl_path, 'r') as f:
                body_template = f.read()
                
            # Basic personalization (firstname)
            # We need the lead's name. Check input sheet or derive from email?
            # For speed, let's try to lookup in self.lead_map if we had it, 
            # or just generic greeting if name is missing.
            # actually `process_replies` doesn't pass lead details.
            # Let's simple check if we can get name from display name or just use "Hi"
            # For now, let's just use "Hi there," if we can't find it easily? 
            # Or better, read the input sheet again? We loaded emails.
            # Let's assume we can regex the first name from the to_email line or just say "Hi,"
            
            # Simple variable injection
            # Variables: {{ first_name }}, {{ sender_name }}
            # Sender Name: "Web4Guru Team" (or specific sender if we knew who sent it)
            # The inbox_id has the sender name in mailreef?
            
            # Get sender from inbox for consistency?
            inbox_status = self.mailreef.get_inbox_status(inbox_id)
            sender_name = inbox_status.get("sender_name", "Web4Guru Team")
            
            # Use a safe fallback for first name
            first_name = "there"
            
            body = body_template.replace("{{ first_name }}", first_name) \
                                .replace("{{ sender_name }}", sender_name)
                                
            # Subject: Re: <Original Subject>? Mailreef usually handles threading if we reply to thread?
            # Mailreef send API doesn't fully support "Reply-To-Thread" natively in the simple `send_email` method
            # we typically just send a new email with the same subject prefixed "Re:"?
            # Wait, `send_email` just takes to/subj/body.
            # To thread properly, we usually need References headers.
            # Mailreef API v1 might not support custom headers in the simple endpoint.
            # But if we send to the same person with "Re: <Subject>", clients often thread it.
            
            # Let's try to find original subject from the reply object? 
            # Passed to this method? No.
            # We need to pass logic.
            pass # Implemented in process_replies
            
        except Exception as e:
            logger.error(f"Error preparing auto-reply: {e}")

    def process_replies(self):
        state = self.load_state()
        last_check_str = state.get("last_check")
        processed_msg_ids = set(state.get("processed_msg_ids", []))
        
        # Add a 1-hour safety overlap to catch anything missed by transient errors
        try:
            last_check_dt = datetime.fromisoformat(last_check_str)
        except:
            last_check_dt = datetime.now() - timedelta(hours=24)
            
        safety_check_dt = last_check_dt - timedelta(hours=1)
        safety_check_str = safety_check_dt.isoformat()
        
        logger.info(f"Checking for replies since {safety_check_str} (Safety Overlap: 1h)")
        replies = self.get_inbox_replies(safety_check_str)
        logger.info(f"Found {len(replies)} potential replies in window")
        
        # Sort replies by date to process chronologically
        replies.sort(key=lambda x: x.get('date', ''))
        
        latest_successful_dt = last_check_dt
        
        for reply in replies:
            msg_id = reply.get('msg_id', '')
            if msg_id and msg_id in processed_msg_ids:
                logger.debug(f"⏭️ [SKIP] Already processed reply ID {msg_id}")
                continue
                
            from_email = reply.get('from_email')
            body = reply.get('body', '')
            subject = reply.get('subject', '')
            reply_date_str = reply.get('date')
            
            logger.info(f"📩 Processing reply from {from_email}...")
            
            # 2. Sentiment + Intent
            sentiment = self.analyze_sentiment(body)
            logger.info(f"Sentiment for {from_email}: {sentiment}")

            # Lead lookup for intent context + draft personalization
            lead_record = {}
            original_outbound = ""
            try:
                self.sheets_client._fetch_all_records()
                lead_record = self.sheets_client._cache.get(from_email.lower(), {}) or {}
                if not lead_record and "@" in from_email:
                    domain = from_email.split("@", 1)[1].lower()
                    if domain not in {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com"}:
                        for rec in self.sheets_client._cache.values():
                            if "@" in str(rec.get("email", "")) and rec["email"].split("@", 1)[1].lower() == domain:
                                lead_record = rec
                                break
                original_outbound = lead_record.get("email_1_content", "") or ""
            except Exception as e:
                logger.warning(f"Could not look up lead context for {from_email}: {e}")

            intent = self.classify_intent(body, lead_record.get("role", ""))
            logger.info(f"Intent for {from_email}: {intent}")

            # AI-drafted response for actionable intents
            suggested_reply = ""
            if intent in self.DRAFT_INTENTS:
                # Pick the active sender identity for this profile
                sender_identity = {}
                try:
                    profile_cfg = automation_config.CAMPAIGN_PROFILES.get(self.profile_name, {})
                    override_name = profile_cfg.get("sender_identities_override")
                    identities = getattr(automation_config, override_name, None) if override_name else None
                    identities = identities or getattr(automation_config, "SENDER_IDENTITIES", {})
                    sender_identity = identities.get("default") or next(iter(identities.values()), {})
                except Exception:
                    pass
                suggested_reply = self.draft_reply_response(
                    intent, body, original_outbound, lead_record, sender_identity
                )
                if suggested_reply:
                    logger.info(f"📝 [DRAFT] Generated suggested reply for {from_email} (intent={intent})")

            # 2b. OPT-OUT ENFORCEMENT: Suppress negative replies immediately
            #     Trigger on either coarse sentiment OR fine-grained intent.
            if sentiment == 'negative' or intent in self.NEGATIVE_INTENTS:
                try:
                    from suppression_manager import SuppressionManager
                    sm = SuppressionManager()
                    sm.add_to_suppression(from_email, f"OPT_OUT_{self.profile_name}")
                    logger.info(f"🚫 [OPT-OUT] Suppressed {from_email} after negative reply")
                except Exception as e:
                    logger.error(f"Failed to suppress opt-out {from_email}: {e}")

                try:
                    self.sheets_client.update_lead_status(
                        email=from_email,
                        status="opted_out"
                    )
                except Exception as e:
                    logger.error(f"Failed to update sheet for opt-out {from_email}: {e}")

            # 3. Log to Google Sheets
            reply_data = {
                'received_at': reply_date_str or datetime.now().isoformat(),
                'from_email': from_email,
                'subject': subject,
                'entire_thread': body,
                'sentiment': sentiment,
                'intent': intent,
                'suggested_reply': suggested_reply,
                'original_sender': reply.get('inbox_email'),
                'thread_id': reply.get('thread_id', reply.get('conversation_id')),
                'school_name': lead_record.get('school_name', ''),
                'role': lead_record.get('role', ''),
                'from_name': (
                    f"{lead_record.get('first_name', '')} {lead_record.get('last_name', '')}".strip()
                    or reply.get('from_name', '')
                ),
            }
            try:
                self.sheets_client.log_reply(reply_data)
            except Exception as e:
                logger.error(f"❌ Failed to log to sheets: {e}")
                continue # Do not add to processed_ids if it failed to log
                
            # If we reached here, logging was successful. 
            # SAVE STATE IMMEDIATELY to prevent redunant processing on crash.
            if msg_id:
                processed_msg_ids.add(msg_id)
            
            # Update latest successful timestamp
            if reply_date_str:
                try:
                    reply_dt = datetime.fromisoformat(reply_date_str.replace('Z', '+00:00'))
                    reply_dt = reply_dt.replace(tzinfo=None)
                    if reply_dt > latest_successful_dt:
                        latest_successful_dt = reply_dt
                except Exception as te:
                    logger.error(f"Time parse error: {te}")

            # Persistent save
            state["last_check"] = latest_successful_dt.isoformat()
            state["processed_msg_ids"] = list(processed_msg_ids)[-5000:]
            self.save_state(state)
                
            
            # 4. (Removed Telegram Alert functionality)
            if sentiment == 'positive':
                
                # 5. AUTO-REPLY LOGIC
                profile_config = automation_config.CAMPAIGN_PROFILES[self.profile_name]
                if profile_config.get("auto_reply_template"):
                    logger.info(f"🤖 [AUTO-REPLY] Attempting to auto-reply to {from_email}")
                    # Need inbox_id. we have inbox_email from 'original_sender'
                    inbox_email = reply.get('inbox_email')
                    if inbox_email and '@' in inbox_email:
                        self.send_auto_reply(from_email, reply_data['thread_id'], inbox_email, subject)
                    else:
                        logger.error(f"Cannot auto-reply: Inbox email not found in reply data")
                        
        # Save the updated state so we don't process these again
        state["last_check"] = latest_successful_dt.isoformat()
        # Keep only the last 5000 processed IDs to prevent the state file from growing infinitely
        state["processed_msg_ids"] = list(processed_msg_ids)[-5000:]
        self.save_state(state)
        logger.info("✅ Reply check cycle completed.")
                        
    def send_auto_reply(self, to_email: str, thread_id: str, inbox_id: str, original_subject: str):
        """Sends the follow-up pitch (Email 2) as an auto-reply."""
        profile_config = automation_config.CAMPAIGN_PROFILES[self.profile_name]
        template_file = profile_config.get("auto_reply_template")
        
        if not template_file:
            return

        base_tpl_dir = profile_config.get("templates_dir", "templates")
        full_tpl_path = os.path.join(BASE_DIR, base_tpl_dir, template_file)
        
        if not os.path.exists(full_tpl_path):
             logger.error(f"Auto-reply template not found at {full_tpl_path}")
             return

        try:
            with open(full_tpl_path, 'r') as f:
                body_template = f.read()
                
            # Get sender from inbox for consistency
            try:
                inbox_status = self.mailreef.get_inbox_status(inbox_id)
                sender_name = inbox_status.get("sender_name", "Web4Guru Team")
            except:
                sender_name = "Web4Guru Team"
            
            # Prepare Subject
            new_subject = original_subject
            if not new_subject.lower().startswith("re:"):
                new_subject = f"Re: {new_subject}"
            
            # Extract first name (naive)
            # Try to grab from sheet if available? 
            # self.sheets_client.input_sheet might have it but loading all records is expensive just for lookup
            # Let's try to infer from name, or use "there"
            # Actually, `send_email` is just a fire-and-forget.
            # Let's use "there" for safety unless we really want it.
            first_name = "there"
            
            body = body_template.replace("{{ first_name }}", first_name) \
                                .replace("{{ sender_name }}", sender_name)
            
            logger.info(f"Sending auto-reply to {to_email} from {inbox_id}...")
            res = self.mailreef.send_email(inbox_id, to_email, new_subject, body)
            
            if res.get("success"):
                logger.info(f"✅ Auto-reply sent successfully to {to_email}")
            else:
                 logger.error(f"❌ Auto-reply failed: {res.get('error')}")

        except Exception as e:
            logger.error(f"Error preparing auto-reply: {e}")

    def run_daemon(self):
        logger.info(f"Starting Reply Watcher daemon (every {CHECK_INTERVAL_MINUTES}m)")
        while True:
            try:
                self.process_replies()
            except Exception as e:
                logger.error(f"Error in daemon: {e}")
            time.sleep(CHECK_INTERVAL_MINUTES * 60)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--profile", type=str, default="IVYBOUND", help="Campaign profile (IVYBOUND or STRATEGY_B)")
    args = parser.parse_args()
    
    watcher = ReplyWatcher(profile_name=args.profile)
    try:
        if args.daemon:
            watcher.run_daemon()
        else:
            watcher.process_replies()
    finally:
        lock_util.release_lock(watcher.lock_name)

if __name__ == "__main__":
    main()
