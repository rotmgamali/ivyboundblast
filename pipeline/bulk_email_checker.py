import requests
import logging
import urllib.parse

logger = logging.getLogger(__name__)

BULK_EMAIL_CHECKER_API_KEY = "VJIHKeGCrvXfUEpFq6wAyBDTQY8n2kW9"

def verify_email_bulk(email: str) -> dict:
    """
    Verifies an email using the BulkEmailChecker API.
    Returns: {"valid": True/False, "reason": "Api response info"}
    """
    if not email or "@" not in email:
        return {"valid": False, "reason": "invalid_format"}
        
    encoded_email = urllib.parse.quote(email)
    url = f"https://api.bulkemailchecker.com/real-time/?key={BULK_EMAIL_CHECKER_API_KEY}&email={encoded_email}"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # Check credit limit explicitly to alert user
        credits = data.get('creditsRemaining')
        if credits is not None and int(credits) <= 0:
            logger.error(f"FATAL: BulkEmailChecker Out of Credits! Cannot continue verification.")
            raise Exception("BulkEmailChecker Out of Credits")
        
        # BulkEmailChecker returns 'status': 'passed', 'failed', 'unknown'
        status = data.get('status', 'unknown')
        details = data.get('details', '')
        
        # We only want guaranteed valid emails for cold outreach
        if status == 'passed':
            # Role accounts might be 'passed' but we can check isRoleAccount flag
            if data.get('isRoleAccount', False):
                return {"valid": False, "reason": f"role_based ({details})"}
            return {"valid": True, "reason": "passed"}
        elif status == 'failed':
            return {"valid": False, "reason": f"failed: {details}"}
        else:
            return {"valid": False, "reason": f"{status} ({details})"}
            
    except Exception as e:
        logger.error(f"BulkEmailChecker API Error for {email}: {e}")
        # Fail closed to preserve sender reputation 
        return {"valid": False, "reason": f"api_error: {str(e)}"}
