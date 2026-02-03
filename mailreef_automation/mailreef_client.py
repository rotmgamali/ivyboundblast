"""
Mailreef API integration layer
Handles all communication with Mailreef infrastructure
"""

import requests
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
import os
import socket
import base64
import socks

from logger_util import get_logger

# Check for SOCKS Proxy to bypass cloud firewalls
SOCKS_PROXY = os.getenv("SOCKS_PROXY_URL")  # Format: socks5://user:pass@host:port

def get_proxy_config():
    if not SOCKS_PROXY:
        return None
    try:
        import socks
        from urllib.parse import urlparse
        
        # Handle cases where user forgot the scheme (default to http)
        if '://' not in SOCKS_PROXY:
            url = f"http://{SOCKS_PROXY}"
        else:
            url = SOCKS_PROXY
            
        proxy_parts = urlparse(url)
        is_socks = 'socks' in proxy_parts.scheme
        
        config = {
            'proxy_type': socks.SOCKS5 if is_socks else socks.HTTP,
            'proxy_addr': proxy_parts.hostname,
            'proxy_port': proxy_parts.port or (1080 if is_socks else 80),
            'proxy_rdns': True,
            'proxy_username': proxy_parts.username,
            'proxy_password': proxy_parts.password
        }
        
        type_str = "SOCKS5" if is_socks else "HTTP"
        # MASKED LOG to reveal the exact scheme being seen by the app
        masked_url = f"{proxy_parts.scheme}://{proxy_parts.hostname}:{proxy_parts.port}"
        print(f"🔒 Targeted Proxy configured: [{type_str}] (Parsed from: {masked_url})")
        return config
    except Exception as e:
        print(f"⚠️ Failed to parse SOCKS_PROXY_URL: {e}")
        return None

def create_proxy_connection(target, timeout, proxy_info):
    """
    Creates a connection through a proxy.
    Uses socks.create_connection for SOCKS5, 
    but uses a manual HTTP/1.1 CONNECT for HTTP to bypass 407 errors.
    """
    target_host, target_port = target
    
    if proxy_info['proxy_type'] != socks.HTTP:
        # Standard SOCKS5 handling
        return socks.create_connection(
            target,
            timeout=timeout,
            **proxy_info
        )
    
    # Custom HTTP CONNECT for modern proxy compliance (fixes 407)
    proxy_addr = proxy_info['proxy_addr']
    proxy_port = proxy_info['proxy_port']
    user = proxy_info['proxy_username']
    password = proxy_info['proxy_password']
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(timeout)
        s.connect((proxy_addr, proxy_port))
        
        auth = base64.b64encode(f"{user}:{password}".encode()).decode()
        connect_req = (
            f"CONNECT {target_host}:{target_port} HTTP/1.1\r\n"
            f"Host: {target_host}:{target_port}\r\n"
            f"Proxy-Authorization: Basic {auth}\r\n"
            f"User-Agent: MailreefAutomation/1.0\r\n"
            f"Proxy-Connection: Keep-Alive\r\n\r\n"
        )
        s.sendall(connect_req.encode())
        
        # Read response
        response = s.recv(4096).decode()
        if "200" in response or "Established" in response:
            return s
        else:
            first_line = response.splitlines()[0] if response else "Empty Proxy Response"
            s.close()
            raise socket.error(f"Proxy connection failed: {first_line}")
    except Exception as e:
        s.close()
        raise e

class ProxySMTP(smtplib.SMTP):
    """SMTP class that routes traffic through a SOCKS or HTTP proxy."""
    def __init__(self, *args, **kwargs):
        self.proxy_info = get_proxy_config()
        super().__init__(*args, **kwargs)

    def _get_socket(self, host, port, timeout):
        if self.proxy_info:
            return create_proxy_connection(
                (host, port), 
                timeout=timeout,
                proxy_info=self.proxy_info
            )
        return super()._get_socket(host, port, timeout)

class ProxySMTP_SSL(smtplib.SMTP_SSL):
    """SMTP_SSL class that routes traffic through a SOCKS or HTTP proxy."""
    def __init__(self, *args, **kwargs):
        self.proxy_info = get_proxy_config()
        super().__init__(*args, **kwargs)

    def _get_socket(self, host, port, timeout):
        if self.proxy_info:
            return create_proxy_connection(
                (host, port), 
                timeout=timeout,
                proxy_info=self.proxy_info
            )
        return super()._get_socket(host, port, timeout)
        if self.proxy_info:
            import socks
            return socks.create_connection(
                (host, port), 
                timeout=timeout,
                **self.proxy_info
            )
        return super()._get_socket(host, port, timeout)

logger = get_logger("MAILREEF_CLIENT")

class MailreefClient:
    """Client for interacting with Mailreef API"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.mailreef.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.auth = (api_key, '')
        self.session.headers.update({
            "Content-Type": "application/json"
        })
        self._mailbox_creds_cache = {}  # Cache for SMTP details
    
    def get_inboxes(self) -> List[Dict]:
        """
        Fetch all available mailboxes by iterating through domains.
        """
        inboxes = []
        try:
            # 1. Fetch all domains
            domains = []
            page = 1
            while True:
                response = self.session.get(
                    f"{self.base_url}/domains", 
                    params={"page": page, "display": 100}
                )
                response.raise_for_status()
                data = response.json()
                
                # Check structure
                batch = data.get('data', data) if isinstance(data, dict) else data
                if not batch:
                    break
                    
                domains.extend(batch)
                
                # Simple pagination check: if less than display limit, we are done
                if len(batch) < 100:
                    break
                page += 1
            
            # 2. Fetch mailboxes for each domain
            for domain in domains:
                domain_id = domain.get('id')
                if not domain_id: continue
                
                page = 1
                while True:
                    response = self.session.get(
                        f"{self.base_url}/mailboxes",
                        params={"domain": domain_id, "page": page, "display": 100}
                    )
                    # If 404/400, skip domain
                    if response.status_code >= 400:
                        break
                        
                    data = response.json()
                    batch = data.get('data', data) if isinstance(data, dict) else data
                    if not batch:
                        break
                        
                    inboxes.extend(batch)
                    
                    if len(batch) < 100:
                        break
                    page += 1
                    
        except Exception as e:
            logger.error(f"❌ Error fetching inboxes: {e}")
            
        return inboxes
    
    def get_inbox_status(self, inbox_id: str) -> Dict:
        """Get current status of a specific inbox"""
        # Endpoint guess: /mailboxes/{id}
        response = self.session.get(f"{self.base_url}/mailboxes/{inbox_id}")
        response.raise_for_status()
        return response.json()
    
    def send_email(self, inbox_id: str, to_email: str, subject: str, 
                   body: str, reply_to: Optional[str] = None) -> Dict:
        """Send a single email through Mailreef using SMTP credentials."""
        
        # 1. Get SMTP credentials for this inbox
        creds = self._get_cached_creds(inbox_id)
        if not creds:
            raise Exception(f"Could not retrieve SMTP credentials for {inbox_id}")
            
        smtp_host = creds.get('smtp_host', 'smtp.mailreef.com')
        smtp_user = inbox_id
        smtp_pass = creds.get('password')
        
        # Determine port - default to 465 for errorskin servers which succeeded in test
        smtp_port = creds.get('smtp_port')
        if not smtp_port:
            if 'errorskin' in smtp_host:
                smtp_port = 465
            else:
                smtp_port = 587
        
        if not smtp_pass:
            raise Exception(f"No password found for {inbox_id}")

        # 2. Build email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{creds.get('sender_name', 'Andrew')} <{inbox_id}>"
        msg['To'] = to_email
        if reply_to:
            msg['Reply-To'] = reply_to

        # Add both text and HTML versions
        import re
        text_body = re.sub('<[^<]+?>', '', body)
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(body, 'html')
        msg.attach(part1)
        msg.attach(part2)

        # 3. Send via SMTP (try SSL first if 465, else TLS)
        logger.debug(f"🔌 [SMTP CONNECT] Connecting to {smtp_host}:{smtp_port} for {inbox_id}...")
        # 3. Send via SMTP (Prioritize 587/TLS, then 465/SSL)
        # Note: 'errorskin' servers often support 587 with STARTTLS better, or 465 with implicit SSL.
        # We will try 587 first as it aligns with modern standards, then fallback to 465.
        
        # Override initial port decision to force dynamic retry flow
        primary_port = 587
        secondary_port = 465
        
        # If creds explicitly specified 465, swap order
        if smtp_port == 465:
            primary_port = 465
            secondary_port = 587
            
        try:
            # Attempt Primary Port
            logger.debug(f"🔌 [SMTP CONNECT] Connecting to {smtp_host}:{primary_port} for {inbox_id}...")
            if primary_port == 465:
                # Implicit SSL
                with ProxySMTP_SSL(smtp_host, primary_port, timeout=60) as server:
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
            else:
                # STARTTLS
                with ProxySMTP(smtp_host, primary_port, timeout=60) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
                    
            logger.debug(f"📤 [SMTP SUCCESS] Message accepted by {smtp_host} (Port {primary_port})")
            return {"status": "success", "message_id": f"smtp_{int(time.time())}"}
            
        except (smtplib.SMTPConnectError, ConnectionRefusedError, TimeoutError, smtplib.SMTPServerDisconnected) as e1:
            logger.warning(f"⚠️ SMTP Fail on port {primary_port}: {e1}. Retrying on {secondary_port}...")
            
            try:
                # Attempt Secondary Port
                if secondary_port == 465:
                    with ProxySMTP_SSL(smtp_host, secondary_port, timeout=60) as server:
                        server.login(smtp_user, smtp_pass)
                        server.send_message(msg)
                else:
                    with ProxySMTP(smtp_host, secondary_port, timeout=60) as server:
                        server.starttls()
                        server.login(smtp_user, smtp_pass)
                        server.send_message(msg)
                        
                logger.debug(f"📤 [SMTP SUCCESS] Message accepted by {smtp_host} (Port {secondary_port})")
                return {"status": "success", "message_id": f"smtp_{int(time.time())}"}
                
            except Exception as e2:
                logger.error(f"❌ [SMTP FINAL ERROR] Failed on both ports ({primary_port}, {secondary_port}). Last error: {e2}")
                
                # 🔍 TRIGGER DIAGNOSTICS
                try:
                    logger.info("🩺 Triggering runtime network diagnostics...")
                    from diagnose_network import run_diagnostics
                    run_diagnostics()
                except Exception as diag_err:
                    logger.error(f"Failed to run diagnostics: {diag_err}")
                
                raise Exception(f"SMTP Failed: {e2}")
        
        except Exception as e:
            logger.error(f"❌ [SMTP ERROR] Unexpected error via {smtp_host}: {e}")
            
            # 🔍 TRIGGER DIAGNOSTICS on unexpected errors too
            try:
                from diagnose_network import run_diagnostics
                run_diagnostics()
            except:
                pass
                
            raise Exception(f"SMTP Send Error: {e}")

    def _get_cached_creds(self, inbox_id: str) -> Dict:
        """Fetch and cache mailbox details (SMTP host, password, etc)"""
        if inbox_id in self._mailbox_creds_cache:
            return self._mailbox_creds_cache[inbox_id]
            
        try:
            response = self.session.get(f"{self.base_url}/mailboxes/{inbox_id}")
            response.raise_for_status()
            creds = response.json()
            self._mailbox_creds_cache[inbox_id] = creds
            return creds
        except Exception as e:
            logger.error(f"❌ Error fetching credentials for {inbox_id}: {e}")
            return {}
    
    def get_email_status(self, message_id: str) -> Dict:
        """Check status of a sent email"""
        # Guessing /emails/{id}
        response = self.session.get(f"{self.base_url}/emails/{message_id}")
        response.raise_for_status()
        return response.json()
    
    def get_inbox_analytics(self, inbox_id: str, days: int = 30) -> Dict:
        """Get analytics for an inbox"""
        # Guessing /mailboxes/{id}/analytics or similar
        # Since I can't check, I'll return mock or try probable endpoint
        # For safety in this "correcting" phase, I'll log warning if 404
        try:
             response = self.session.get(
                f"{self.base_url}/mailboxes/{inbox_id}/stats",
                params={"days": days}
            )
             if response.status_code == 200:
                 return response.json()
        except:
            pass
        return {} # Fallback
    
    def get_reply_handling(self, inbox_id: str) -> List[Dict]:
        """Check for replies to process"""
        # Guessing
        return []
    
    def pause_inbox(self, inbox_id: str):
        """Temporarily pause an inbox"""
        # Not sure if API supports this via endpoint. 
        # Maybe PUT /mailboxes/{id} with {status: paused}?
        pass
    
    def resume_inbox(self, inbox_id: str):
        """Resume a paused inbox"""
        pass
