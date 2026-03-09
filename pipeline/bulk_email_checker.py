import requests
import logging
import urllib.parse
import time

logger = logging.getLogger(__name__)

BULK_EMAIL_CHECKER_API_KEY = "VJIHKeGCrvXfUEpFq6wAyBDTQY8n2kW9"

GENERIC_EMAIL_PREFIXES = {
    "info", "admin", "office", "contact", "support", "help", "hello",
    "sales", "marketing", "billing", "accounts", "hr", "jobs", "careers",
    "webmaster", "postmaster", "hostmaster", "abuse", "noreply", "no-reply",
    "communications", "media", "press", "news", "newsletter", "subscribe",
    "frontoffice", "front.office", "reception", "registrar", "admissions",
    "enrollment", "enroll", "attendance", "cashier", "feedback",
    "general", "main", "team", "staff", "department", "inquiry",
    "website", "websitecontact", "web", "siteadmin",
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
                if data.get('isRoleAccount', False):
                    return {"valid": False, "reason": f"role_based ({details})"}
                return {"valid": True, "reason": "passed"}
            elif status == 'failed':
                return {"valid": False, "reason": f"failed: {details}"}
            else:
                return {"valid": False, "reason": f"{status} ({details})"}
                
        except Exception as e:
            if attempt < retries - 1:
                logger.warning(f"Error checking {email}: {e}. Retrying...")
                time.sleep(2)
                continue
            logger.error(f"BulkEmailChecker API Error for {email}: {e}")
            return {"valid": False, "reason": f"api_error: {str(e)}"}
            
    return {"valid": False, "reason": "max_retries_exceeded"}
