import logging
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)


class WarmingOrchestrator:
    """
    Manages inbox warming to maintain sender reputation.
    """

    WARMING_CONFIG = {
        "daily_volume_per_inbox": 50,
        "ramp_up_days": 14,
        "target_warming_quota": 33000  # Monthly warming emails
    }

    def __init__(self, smartlead_client, inbox_rotator, config):
        self.client = smartlead_client
        self.rotator = inbox_rotator
        self.config = config

    def calculate_warming_needs(self) -> dict:
        """
        Calculate how many inboxes need warming and at what volume.
        """
        self.rotator.refresh_pool()
        total_inboxes = len(self.rotator.inbox_pool)

        # Calculate monthly warming needs
        monthly_warming = self.WARMING_CONFIG["target_warming_quota"]
        daily_warming = monthly_warming // 30

        return {
            "inboxes_needing_warming": total_inboxes,
            "daily_volume_per_inbox": daily_warming // total_inboxes if total_inboxes > 0 else 10,
            "total_daily_warming": daily_warming
        }

    def assign_warming_campaigns(self) -> Dict:
        """
        Assign warming campaigns to inboxes that need reputation building.
        """
        needs = self.calculate_warming_needs()
        inboxes_for_warming = [i.id for i in self.rotator.inbox_pool]

        if inboxes_for_warming:
            campaign = self.client.create_warming_campaign(
                inbox_ids=inboxes_for_warming,
                daily_volume=needs["daily_volume_per_inbox"]
            )
            logger.info(f"Warming campaign created for {len(inboxes_for_warming)} inboxes")
            return campaign

        logger.warning("No inboxes available for warming")
        return {}

    def monitor_warming_progress(self) -> dict:
        """
        Check warming progress and adjust if needed.
        """
        campaigns = self.client.get_warming_campaigns()

        total_sent = sum(c.get("emails_sent", 0) for c in campaigns)
        healthy_count = sum(1 for c in campaigns if c.get("health_score", 0) > 0.7)

        return {
            "total_warming_emails_sent": total_sent,
            "healthy_inboxes": healthy_count,
            "campaigns_active": len(campaigns),
            "progress_percentage": (total_sent / self.WARMING_CONFIG["target_warming_quota"]) * 100 if self.WARMING_CONFIG["target_warming_quota"] > 0 else 0
        }
