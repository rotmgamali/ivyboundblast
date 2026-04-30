"""
BulkEmailChecker.com integration — paid email verification API.

Real-time endpoint:
    GET https://api.bulkemailchecker.com/real-time/?key=KEY&email=EMAIL

Status field meanings:
    "passed"  → mailbox confirmed receiving — SAFE to send
    "unknown" → catchall MX (event="is_catchall") — most B2B real, OK to send
    "failed"  → invalid/blacklisted/dead — DO NOT send
"""
from __future__ import annotations
import os
import json
import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

logger = logging.getLogger("lead_engine.bulkemailchecker")

API_KEY = os.getenv("EMAIL_CHECKER_API_KEY") or os.getenv("BULKEMAILCHECKER_API_KEY")
BASE_URL = "https://api.bulkemailchecker.com"


@dataclass
class VerifyResult:
    email: str
    status: str            # "passed" | "unknown" | "failed" | "error"
    event: str             # API event field e.g. "is_catchall", "blacklisted", "no_mx", etc.
    is_catchall: bool
    is_disposable: bool
    is_role_account: bool
    is_free_service: bool
    details: str
    credits_remaining: Optional[int] = None
    raw: Optional[Dict] = None

    @property
    def deliverable(self) -> bool:
        """True if email is safe to send to."""
        return self.status in ("passed", "unknown") and not self.is_disposable


class BulkEmailChecker:
    def __init__(self, api_key: Optional[str] = None, max_retries: int = 2):
        self.api_key = api_key or API_KEY
        if not self.api_key:
            raise ValueError("EMAIL_CHECKER_API_KEY not set in env")
        self.max_retries = max_retries
        self.session = requests.Session()
        self._last_credits = None

    def verify(self, email: str, timeout: int = 30) -> VerifyResult:
        email = (email or "").strip().lower()
        if not email or "@" not in email:
            return VerifyResult(email, "failed", "invalid_format", False, False, False, False,
                                "Invalid email format")

        url = f"{BASE_URL}/real-time/?key={self.api_key}&email={quote(email)}"

        last_err = ""
        for attempt in range(self.max_retries + 1):
            try:
                r = self.session.get(url, timeout=timeout)
                if r.status_code != 200:
                    last_err = f"HTTP {r.status_code}: {r.text[:200]}"
                    time.sleep(1.5 ** attempt)
                    continue

                data = r.json()
                status = (data.get("status") or "error").lower()
                event = (data.get("event") or "").lower()
                self._last_credits = data.get("creditsRemaining")

                return VerifyResult(
                    email=email,
                    status=status,
                    event=event,
                    is_catchall=event == "is_catchall",
                    is_disposable=bool(data.get("isDisposable")),
                    is_role_account=bool(data.get("isRoleAccount")),
                    is_free_service=bool(data.get("isFreeService")),
                    details=data.get("details", ""),
                    credits_remaining=self._last_credits,
                    raw=data,
                )
            except Exception as e:
                last_err = str(e)[:200]
                time.sleep(1.5 ** attempt)

        return VerifyResult(email, "error", "api_error", False, False, False, False, last_err)

    def credits_remaining(self) -> Optional[int]:
        """Returns the cached credits-remaining count from the last API call."""
        return self._last_credits


# Convenience wrapper for backward compat with lead_engine.email_verifier interface
def verify_email(email: str) -> Dict:
    """Drop-in compatible verify function. Returns a dict with the standard
    keys: email, status, mx_host, is_catch_all, reason — so existing code can
    swap from the DNS-only verifier to this paid verifier without changes."""
    bec = BulkEmailChecker()
    r = bec.verify(email)
    # Map BEC status to our internal vocab
    if r.status == "passed":
        internal_status = "verified"
    elif r.status == "unknown" and r.is_catchall:
        internal_status = "catch_all"
    elif r.is_disposable:
        internal_status = "disposable"
    else:
        internal_status = "invalid"
    return {
        "email": r.email,
        "status": internal_status,
        "mx_host": "",  # API doesn't return MX
        "is_catch_all": r.is_catchall,
        "is_disposable": r.is_disposable,
        "is_role_account": r.is_role_account,
        "deliverable": r.deliverable,
        "reason": r.details,
        "credits_remaining": r.credits_remaining,
    }


if __name__ == "__main__":
    # Quick smoke test
    import sys
    if len(sys.argv) < 2:
        print("Usage: python bulkemailchecker.py <email>")
        sys.exit(1)
    bec = BulkEmailChecker()
    r = bec.verify(sys.argv[1])
    print(json.dumps({
        "email": r.email, "status": r.status, "event": r.event,
        "deliverable": r.deliverable, "details": r.details,
        "credits_remaining": r.credits_remaining,
    }, indent=2))
