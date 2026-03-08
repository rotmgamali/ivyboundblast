import os
import requests
import logging

logger = logging.getLogger(__name__)

MILLION_VERIFIER_API_KEY = "3XFKZiL1Cy3OPfBP4ZdjEAOg6"

def verify_email_millionverifier(email: str) -> dict:
    """
    Verifies an email using the MillionVerifier API.
    Returns: {"valid": True/False, "reason": "Api response info"}
    """
    if not email or "@" not in email:
        return {"valid": False, "reason": "invalid_format"}
        
    url = f"https://api.millionverifier.com/api/v3/?api={MILLION_VERIFIER_API_KEY}&email={email}&timeout=10"
    
    try:
        response = requests.get(url, timeout=12)
        response.raise_for_status()
        data = response.json()
        
        # MillionVerifier returns 'result': 'ok', 'catch_all', 'disposable', 'invalid', 'unknown'
        result = data.get('result', 'unknown')
        subresult = data.get('subresult', '')
        
        # We only want guaranteed valid emails for cold outreach
        if result == 'ok':
            # Role accounts (admin@, info@) might technically be 'ok' but have a subresult
            if data.get('role', False):
                return {"valid": False, "reason": f"role_based ({subresult})"}
            return {"valid": True, "reason": "ok"}
        elif result == 'error':
            error_msg = data.get('error', 'unknown API error')
            if 'Insufficient credits' in error_msg:
                logger.error(f"FATAL: MillionVerifier Out of Credits! Cannot continue verification.")
                raise Exception("MillionVerifier Out of Credits")
            return {"valid": False, "reason": f"error: {error_msg}"}
        else:
            return {"valid": False, "reason": f"{result} ({subresult})"}
            
    except Exception as e:
        logger.error(f"MillionVerifier API Error for {email}: {e}")
        # Fail closed to preserve sender reputation
        return {"valid": False, "reason": f"api_error: {str(e)}"}
