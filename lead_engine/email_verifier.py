"""
Email verification without external APIs.
Tier 1: Regex syntax check
Tier 2: DNS MX record lookup
Tier 3: Catch-all domain detection
Tier 4: Disposable domain blocklist
"""
import re
import random
import smtplib
import socket
import logging
from dataclasses import dataclass
from typing import Dict, Tuple

import dns.resolver
import dns.exception

from lead_engine.niches import DISPOSABLE_DOMAINS

logger = logging.getLogger("lead_engine.verifier")

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


@dataclass
class VerificationResult:
    email: str
    status: str       # verified, invalid, catch_all, disposable, unknown
    mx_host: str
    is_catch_all: bool
    reason: str


class EmailVerifier:
    """DNS-based email verification with domain-level caching."""

    def __init__(self):
        # Cache: domain -> (has_mx, mx_host, is_catch_all)
        self._domain_cache: Dict[str, dict] = {}

    def verify(self, email: str) -> VerificationResult:
        email = email.strip().lower()

        # Tier 1: Syntax check
        if not EMAIL_REGEX.match(email):
            return VerificationResult(email, "invalid", "", False, "Failed regex syntax check")

        domain = email.split("@")[1]

        # Tier 4: Disposable domain check (before DNS to save time)
        if domain in DISPOSABLE_DOMAINS:
            return VerificationResult(email, "disposable", "", False, f"Disposable domain: {domain}")

        # Check domain cache
        if domain not in self._domain_cache:
            has_mx, mx_host = self._check_mx(domain)
            is_catch_all = self._detect_catch_all(mx_host, domain) if has_mx and mx_host else False
            self._domain_cache[domain] = {
                "has_mx": has_mx, "mx_host": mx_host, "is_catch_all": is_catch_all
            }

        cached = self._domain_cache[domain]

        # Tier 2: MX check
        if not cached["has_mx"]:
            return VerificationResult(email, "invalid", "", False, f"No MX/A records for {domain}")

        # Tier 3: Catch-all detection
        if cached["is_catch_all"]:
            return VerificationResult(
                email, "catch_all", cached["mx_host"], True,
                f"Domain {domain} is catch-all (accepts any address)"
            )

        return VerificationResult(
            email, "verified", cached["mx_host"], False,
            f"MX verified: {cached['mx_host']}"
        )

    def _check_mx(self, domain: str) -> Tuple[bool, str]:
        try:
            records = dns.resolver.resolve(domain, 'MX')
            if records:
                mx_host = str(records[0].exchange).rstrip('.')
                return True, mx_host
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            # Try A record fallback
            try:
                dns.resolver.resolve(domain, 'A')
                return True, ""
            except Exception:
                return False, ""
        except Exception as e:
            logger.debug(f"DNS error for {domain}: {e}")
            return False, ""
        return False, ""

    def _detect_catch_all(self, mx_host: str, domain: str) -> bool:
        if not mx_host:
            return False
        random_local = f"xyzverifytest{random.randint(10000, 99999)}"
        fake_email = f"{random_local}@{domain}"
        try:
            server = smtplib.SMTP(timeout=5)
            server.connect(mx_host)
            server.helo("verify.local")
            server.mail("test@verify.local")
            code, _ = server.rcpt(fake_email)
            server.quit()
            return code == 250
        except Exception:
            return False

    def verify_batch(self, emails: list) -> list:
        return [self.verify(email) for email in emails]
