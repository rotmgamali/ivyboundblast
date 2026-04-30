"""
Deliverability monitoring and alerting
Ensures sender reputation stays healthy
"""

import time
from datetime import datetime
from threading import Thread
from logger_util import get_logger

logger = get_logger("MONITOR")


class DeliverabilityMonitor:
    """Monitors deliverability metrics and adjusts sending"""

    def __init__(self, mailreef_client, config):
        self.mailreef = mailreef_client
        self.config = config
        self.is_running = False
        self.alert_thresholds = {
            "bounce_rate": getattr(config, 'BOUNCE_RATE_THRESHOLD', 0.02),
            "complaint_rate": getattr(config, 'COMPLAINT_RATE_THRESHOLD', 0.003),
        }
        self.thread = None

    def start(self):
        """Start the monitoring loop"""
        if not self.is_running:
            self.is_running = True
            self.thread = Thread(target=self._monitor_loop)
            self.thread.daemon = True
            self.thread.start()
            logger.info("Deliverability monitor started")

    def stop(self):
        """Stop monitoring"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Deliverability monitor stopped")

    def _monitor_loop(self):
        """Continuous monitoring of deliverability metrics"""
        while self.is_running:
            try:
                self.check_all_inboxes()
                self.check_individual_bounces()
                # Check every hour
                for _ in range(3600):
                    if not self.is_running: break
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(300)

    def check_all_inboxes(self):
        """Check all inboxes for health issues"""
        try:
            inboxes = self.mailreef.get_inboxes()

            for inbox in inboxes:
                if not self.is_running: break

                if inbox.get("id") in self.config.INBOX_PAUSED_IDS:
                    continue

                analytics = self.mailreef.get_inbox_analytics(inbox.get("id"), days=7)

                bounce_rate = analytics.get("bounce_rate", 0)
                if bounce_rate > self.alert_thresholds["bounce_rate"]:
                    self._handle_high_bounce(inbox.get("id"), bounce_rate)

                complaint_rate = analytics.get("complaint_rate", 0)
                if complaint_rate > self.alert_thresholds["complaint_rate"]:
                    self._handle_high_complaints(inbox.get("id"), complaint_rate)
        except Exception as e:
            logger.error(f"Error checking inboxes: {e}")

    def check_individual_bounces(self):
        """Scan inbound for bounce notifications and suppress bounced addresses."""
        try:
            from suppression_manager import SuppressionManager
            sm = SuppressionManager()

            inbound = self.mailreef.get_global_inbound(page=1, display=100)
            emails = inbound.get("data", [])

            for email in emails:
                subject = (email.get("subject_line") or "").lower()
                from_addr = (email.get("from_email") or "").lower()

                is_bounce = (
                    "returned mail" in subject
                    or "undeliverable" in subject
                    or "delivery status" in subject
                    or "mail delivery failed" in subject
                    or "postmaster" in from_addr
                    or "mailer-daemon" in from_addr
                )

                if not is_bounce:
                    continue

                # Try to extract the original recipient from the bounce
                body = email.get("body_text") or ""
                import re
                bounced_addresses = re.findall(
                    r'[\w.+-]+@[\w-]+\.[\w.-]+', body
                )

                for addr in bounced_addresses:
                    addr = addr.lower().strip()
                    # Skip our own addresses and common system addresses
                    if any(d in addr for d in ['mailreef', 'truckice', 'competitionhand', 'aspire', 'web4', 'web5']):
                        continue
                    if not sm.is_suppressed(addr):
                        sm.add_to_suppression(addr, "HARD_BOUNCE")
                        logger.info(f"🚫 [BOUNCE] Suppressed bounced address: {addr}")

        except Exception as e:
            logger.error(f"Error checking bounces: {e}")

    def _handle_high_bounce(self, inbox_id, rate):
        """Handle inbox with high bounce rate"""
        try:
            self.mailreef.pause_inbox(inbox_id)
            logger.critical(f"ALERT: Inbox {inbox_id} paused for high bounce rate: {rate:.1%}")
        except Exception as e:
            logger.error(f"Failed to pause inbox {inbox_id}: {e}")

    def _handle_high_complaints(self, inbox_id, rate):
        """Handle inbox with high complaint rate"""
        try:
            self.mailreef.pause_inbox(inbox_id)
            logger.critical(f"CRITICAL: Inbox {inbox_id} paused for spam complaints: {rate:.3%}")
        except Exception as e:
            logger.error(f"Failed to pause inbox {inbox_id}: {e}")
