import requests
import logging
import urllib.parse
import time

logger = logging.getLogger(__name__)

BULK_EMAIL_CHECKER_API_KEY = "VJIHKeGCrvXfUEpFq6wAyBDTQY8n2kW9"

def verify_email_bulk(email: str, retries=3) -> dict:
    """
    Verifies an email using the BulkEmailChecker API.
    Enforces a strict 2.5s delay to never exceed 1,500 req/hour limit.
    """
    if not email or "@" not in email:
        return {"valid": False, "reason": "invalid_format"}
        
    encoded_email = urllib.parse.quote(email)
    url = f"https://api.bulkemailchecker.com/real-time/?key={BULK_EMAIL_CHECKER_API_KEY}&email={encoded_email}"
    
    for attempt in range(retries):
        try:
            # 1500 reqs/hr = 1 req every 2.4s. 2.5s guarantees we stay under limit.
            time.sleep(2.5) 
            
            response = requests.get(url, timeout=15)
            
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
                time.sleep(5)
                continue
            logger.error(f"BulkEmailChecker API Error for {email}: {e}")
            return {"valid": False, "reason": f"api_error: {str(e)}"}
            
    return {"valid": False, "reason": "max_retries_exceeded"}
