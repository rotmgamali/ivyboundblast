import logging
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Inbox:
    id: str
    email: str
    health_score: float
    daily_quota_remaining: int
    last_used: datetime


class InboxRotator:
    """
    Manages inbox rotation for optimal deliverability.
    """

    def __init__(self, mailreef_client, config):
        self.client = mailreef_client
        self.config = config
        self.inbox_pool: List[Inbox] = []
        self.rotation_index = 0

    def refresh_pool(self):
        """
        Fetch latest inbox statuses from Mailreef.
        """
        raw_inboxes = self.client.get_inboxes()
        self.inbox_pool = []
        
        for inx in raw_inboxes:
            try:
                inbox = Inbox(
                    id=inx["id"],
                    email=inx["email"],
                    health_score=inx.get("health_score", 0.5),
                    daily_quota_remaining=inx.get("daily_quota_remaining", 100),
                    last_used=datetime.fromisoformat(inx.get("last_used", "2025-01-01"))
                )
                self.inbox_pool.append(inbox)
            except (KeyError, ValueError) as e:
                logger.warning(f"Could not parse inbox: {e}")
        
        logger.info(f"Inbox pool refreshed: {len(self.inbox_pool)} inboxes available")

    def select_inbox(self, campaign_type: str = None) -> Optional[Inbox]:
        """
        Select the optimal inbox for a given campaign.

        Strategy:
        1. Filter inboxes with acceptable health score
        2. Filter out inboxes with exhausted daily quota
        3. Apply round-robin within healthy inboxes
        """
        healthy_inboxes = [i for i in self.inbox_pool if i.health_score >= 0.3 and i.daily_quota_remaining > 10]

        if not healthy_inboxes:
            logger.warning("No healthy inboxes available")
            return None

        # Sort by health score, then rotate
        healthy_inboxes.sort(key=lambda x: x.health_score, reverse=True)

        # Select using round-robin for variety
        selected = healthy_inboxes[self.rotation_index % len(healthy_inboxes)]
        self.rotation_index += 1

        return selected

    def calculate_campaign_allocation(self) -> dict:
        """
        Calculate how inboxes should be distributed across campaigns.
        """
        total = len(self.inbox_pool)
        return {
            "school": total // 3,
            "real_estate": total // 3,
            "pac": total - (2 * (total // 3))
        }
