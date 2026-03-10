
import logging
import random
import aiohttp
from typing import Dict, Optional, List
from config import Config

logger = logging.getLogger(__name__)

class MailreefRotator:
    """
    Manages rotation of 200+ Mailreef inboxes.
    Fetches active accounts and distributes sending load.
    """
    def __init__(self):
        self.api_key = Config.MAILREEF_API_KEY
        self.inboxes: List[Dict] = []
        self._cursor = 0
        self.base_url = "https://api.mailreef.com/v1" # Hypothetical API endpoint

    async def initialize(self):
        """
        Fetches the list of active inboxes from Mailreef.
        """
        if not self.api_key:
            logger.warning("No MAILREEF_API_KEY. Using mock inboxes.")
            self.inboxes = [
                {"email": f"sender{i}@example.com", "password": "mock_password", "host": "smtp.mailreef.com", "port": 587}
                for i in range(1, 201)
            ]
            return

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/inboxes", # Verify actual endpoint in docs if available
                    headers={"Authorization": f"Bearer {self.api_key}"}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Assuming data structure: {'inboxes': [...]}
                        self.inboxes = [
                            {
                                "email": i.get('email'),
                                "password": i.get('password'),
                                "host": i.get('smtp_host', 'smtp.mailreef.com'),
                                "port": i.get('smtp_port', 587)
                            }
                            for i in data.get('inboxes', [])
                            if i.get('status') == 'active'
                        ]
                        logger.info(f"Loaded {len(self.inboxes)} active inboxes from Mailreef.")
                    else:
                        logger.error(f"Failed to fetch Mailreef inboxes: {resp.status}")
        except Exception as e:
            logger.error(f"Mailreef Init Error: {e}")

    def get_next_sender(self) -> Optional[Dict]:
        """
        Returns the next inbox in the rotation.
        Round-robin strategy to prevent clustering.
        """
        if not self.inboxes:
            return None
        
        inbox = self.inboxes[self._cursor]
        self._cursor = (self._cursor + 1) % len(self.inboxes)
        return inbox

    def get_sender_for_campaign(self, campaign_tag: str) -> Dict:
        """
        Optional: Stickiness logic if needed.
        Currently using simple rotation as per 'Inbox rotation prevents reputation clustering'.
        """
        return self.get_next_sender()
