import os
import requests
import logging
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

SMARTLEAD_API_KEY = os.getenv("SMARTLEAD_API_KEY")
SMARTLEAD_BASE_URL = "https://api.smartlead.ai/v1"

logger = logging.getLogger(__name__)


class SmartleadClient:
    """
    Client for Smartlead inbox warming infrastructure.
    """

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {SMARTLEAD_API_KEY}",
            "Content-Type": "application/json"
        }

    def get_warming_campaigns(self) -> List[Dict]:
        """
        Retrieve all active warming campaigns.
        """
        try:
            response = requests.get(f"{SMARTLEAD_BASE_URL}/warming-campaigns", headers=self.headers)
            response.raise_for_status()
            return response.json().get("campaigns", [])
        except requests.RequestException as e:
            logger.error(f"Smartlead API Error (get_warming_campaigns): {e}")
            return []

    def create_warming_campaign(self, inbox_ids: List[str], daily_volume: int) -> Dict:
        """
        Create a new warming campaign for specified inboxes.
        """
        payload = {
            "inbox_ids": inbox_ids,
            "daily_volume": daily_volume,
            "strategy": "natural_conversations"
        }
        try:
            response = requests.post(
                f"{SMARTLEAD_BASE_URL}/warming-campaigns",
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Smartlead API Error (create_warming_campaign): {e}")
            return {"error": str(e)}

    def get_campaign_status(self, campaign_id: str) -> Dict:
        """
        Check the status and progress of a warming campaign.
        """
        try:
            response = requests.get(
                f"{SMARTLEAD_BASE_URL}/warming-campaigns/{campaign_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Smartlead API Error (get_campaign_status): {e}")
            return {}

    def update_warming_volume(self, campaign_id: str, new_volume: int) -> Dict:
        """
        Adjust the daily volume for a warming campaign.
        """
        payload = {"daily_volume": new_volume}
        try:
            response = requests.put(
                f"{SMARTLEAD_BASE_URL}/warming-campaigns/{campaign_id}",
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Smartlead API Error (update_warming_volume): {e}")
            return {"error": str(e)}
