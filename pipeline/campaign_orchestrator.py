from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd


class CampaignOrchestrator:
    """
    Manages the complete email sequence for a campaign.
    """

    SEQUENCE_CONFIG = {
        1: {"day_offset": 0, "template": "email_1.txt"},
        2: {"day_offset": 4, "template": "email_2.txt"},
        3: {"day_offset": 11, "template": "email_3.txt"}
    }

    def __init__(self, campaign_type: str, config):
        self.campaign_type = campaign_type
        self.config = config
        self.sent_log = []

    def determine_next_sequence(self, lead_row: pd.Series) -> int:
        """
        Determine which email in the sequence this lead should receive next.
        """
        history = str(lead_row.get("email_history", ""))

        if "email_3_sent" in history:
            return None  # Sequence complete

        if "email_2_sent" in history:
            return 3

        if "email_1_sent" in history:
            return 2

        return 1  # Start of sequence

    def should_send_today(self, lead_row: pd.Series, sequence_number: int) -> bool:
        """
        Determine if this lead should receive their next email today.
        """
        if sequence_number == 1:
            return True  # New lead, send first email

        last_send_date_str = lead_row.get(f"email_{sequence_number - 1}_date")
        if not last_send_date_str:
            return False

        try:
            last_send_date = datetime.fromisoformat(str(last_send_date_str))
        except ValueError:
            return False

        days_since = (datetime.now() - last_send_date).days
        required_gap = self.SEQUENCE_CONFIG[sequence_number]["day_offset"] - \
                       self.SEQUENCE_CONFIG[sequence_number - 1]["day_offset"]

        return days_since >= required_gap

    def process_leads(self, leads_df: pd.DataFrame) -> Dict:
        """
        Process all leads and return those ready for sending.
        """
        ready_to_send = []
        dormant_leads = []

        for _, row in leads_df.iterrows():
            next_sequence = self.determine_next_sequence(row)

            if next_sequence is None:
                dormant_leads.append({"lead": row, "reason": "sequence_complete"})
                continue

            if self.should_send_today(row, next_sequence):
                ready_to_send.append({
                    "lead": row,
                    "sequence_number": next_sequence,
                    "template": self.SEQUENCE_CONFIG[next_sequence]["template"]
                })
            else:
                dormant_leads.append({
                    "lead": row,
                    "reason": "waiting_for_timing",
                    "next_sequence": next_sequence
                })

        return {
            "ready_to_send": ready_to_send,
            "dormant_leads": dormant_leads
        }
