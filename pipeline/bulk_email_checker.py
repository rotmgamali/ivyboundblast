import requests
import logging
import urllib.parse
import time

logger = logging.getLogger(__name__)

BULK_EMAIL_CHECKER_API_KEY = "VJIHKeGCrvXfUEpFq6wAyBDTQY8n2kW9"

# ONLY block emails that are truly dead-end / no human reads.
# School-specific prefixes (admissions, office, enrollment, etc.) are KEPT
# because at small schools these are read by principals and directors.
GENERIC_EMAIL_PREFIXES = {
    "noreply", "no-reply", "no.reply", "donotreply", "do-not-reply",
    "webmaster", "postmaster", "hostmaster", "abuse", "mailer-daemon",
    "siteadmin", "websitecontact", "web",
    "newsletter", "subscribe", "unsubscribe",
    "billing", "accounts", "jobs", "careers",
}

def _is_generic_email(email: str) -> bool:
    """Check if email uses a generic/department prefix that no individual reads."""
    local_part = email.split("@")[0].lower().strip()
    # Exact match on prefix
    if local_part in GENERIC_EMAIL_PREFIXES:
        return True
    # Catch patterns like "rhs.webmaster" or "gap.webmaster"
    for prefix in GENERIC_EMAIL_PREFIXES:
        if local_part.endswith(f".{prefix}") or local_part.endswith(f"_{prefix}"):
            return True
    return False

def verify_email_bulk(email: str, retries=1) -> dict:
    """
    Verifies an email using the BulkEmailChecker API.
    Enforces a strict 2.5s delay to never exceed 1,500 req/hour limit.
    Also rejects generic/department catch-all addresses before hitting the API.
    """
    if not email or "@" not in email:
        return {"valid": False, "reason": "invalid_format"}
    
    # Pre-API filter: reject generic department emails
    if _is_generic_email(email):
        logger.info(f"🚫 Rejecting generic/department email: {email}")
        return {"valid": False, "reason": "generic_department_email"}
        
    encoded_email = urllib.parse.quote(email)
    url = f"https://api.bulkemailchecker.com/real-time/?key={BULK_EMAIL_CHECKER_API_KEY}&email={encoded_email}"
    
    for attempt in range(retries):
        try:
            # 1500 reqs/hr = 1 req every 2.4s. 2.5s guarantees we stay under limit.
            time.sleep(2.5) 
            
            response = requests.get(url, timeout=5)
            
            if response.status_code == 429:
                logger.warning(f"BulkEmailChecker Rate Limit Hit (429). Sleeping for 10s... (Attempt {attempt+1}/{retries})")
                time.sleep(10)
                continue
                
            response.raise_for_status()
            data = response.json()
            
            # Check credit limit explicitly
            credits = data.get('creditsRemaining')
            if credits is not None and int(credits) <= 0:
                logger.error(f"FATAL: BulkEmailChecker Out of Credits! Cannot continue verification.")
                raise Exception("BulkEmailChecker Out of Credits")
            
            status = data.get('status', 'unknown')
            details = data.get('details', '')
            
            if status == 'passed':
                # For school outreach, role accounts (admissions@, office@) ARE our targets
                # Don't reject them — they're read by decision-makers at small schools
                if data.get('isRoleAccount', False):
                    logger.info(f"📋 Role account accepted for school outreach: {email}")
                return {"valid": True, "reason": "passed"}
            elif status == 'failed':
                logger.info(f"❌ Email verification FAILED: {email} — {details}")
                return {"valid": False, "reason": f"failed: {details}"}
            else:
                logger.info(f"⚠️ Email verification unclear: {email} — {status}: {details}")
                return {"valid": False, "reason": f"{status} ({details})"}
                
        except Exception as e:
            if attempt < retries - 1:
                logger.warning(f"Error checking {email}: {e}. Retrying...")
                time.sleep(2)
                continue
            logger.error(f"BulkEmailChecker API Error for {email}: {e}")
            return {"valid": False, "reason": f"api_error: {str(e)}"}
            
    return {"valid": False, "reason": "max_retries_exceeded"}
