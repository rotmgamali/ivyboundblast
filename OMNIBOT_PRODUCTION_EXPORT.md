# OMNIBOT COLD EMAIL PLATFORM - PRODUCTION EXPORT

This export contains the complete production-ready codebase.

---

## README
**File:** `README.md`

```markdown
# OmniBot Cold Email Platform

A production-ready cold email platform supporting three distinct campaign pipelines with automated lead enrichment, personalized email generation, and intelligent inbox rotation.

## Tech Stack

- **Serper**: Data enrichment via Google search API
- **Mailreef**: Email sending infrastructure (200 inboxes)
- **Smartlead**: Inbox warming service (33,000 emails/month)
- **OpenAI**: Email content generation (GPT-4o-mini)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your actual API keys
```

Required environment variables:
- `OPENAI_API_KEY`
- `SERPER_API_KEY`
- `MAILREEF_API_KEY`
- `SMARTLEAD_API_KEY`

### 3. Prepare Lead Files

Place your CSV files in the appropriate directory:
- `leads/school/` - School administrator leads
- `leads/real_estate/` - Recent homebuyer leads
- `leads/pac/` - Political donor leads

### 4. Run Campaigns

```bash
# School campaign
python pipeline.py --campaign school --input leads/school/input.csv

# Real Estate campaign
python pipeline.py --campaign real_estate --input leads/real_estate/input.csv

# PAC campaign
python pipeline.py --campaign pac --input leads/pac/input.csv
```

### 5. Run Inbox Warming

```bash
python pipeline.py --warming
```

## Campaign Overview

| Pipeline | Target | Email Sender |
|----------|--------|--------------|
| School | Administrators, Principals, Superintendents | Andrew Rollins |
| Real Estate | Recent Homebuyers (6-18 months) | Andrew Rollins (Aspire Realty) |
| PAC | Political Donors (>$500) | Mark Greenstein |

## Email Sequence

All campaigns use a 3-email sequence:
- **Email 1**: Day 0 - Initial outreach
- **Email 2**: Day 4 - Follow-up with new angle
- **Email 3**: Day 11 - Final touch

## Volume Configuration

- Active emails: 66,000/month (22,000 per campaign)
- Warming emails: 33,000/month
- Total capacity: 99,000/month
- Inboxes: 200 (rotating)

## Directory Structure

```
├── pipeline.py           # Main entry point
├── config.py             # Configuration
├── pipeline/             # Routing and orchestration
├── senders/              # Mailreef integration
├── generators/           # OpenAI email generation
├── warming/              # Smartlead integration
├── templates/            # Email templates
└── leads/                # Input CSV files
```

## License

Proprietary - All rights reserved.

```

---

## Architecture
**File:** `ARCHITECTURE_FINAL.md`

```markdown
# OmniBot Cold Email Platform - Architecture

## Tech Stack
*   **Serper**: Data enrichment via Google search API
*   **Mailreef**: Email sending infrastructure (200 inboxes)
*   **Smartlead**: Inbox warming service (33,000 emails/month)
*   **OpenAI**: Email content generation

## Three Campaign Pipelines

| Pipeline | Target Audience | Enrichment Strategy |
|----------|-----------------|---------------------|
| **School** | School administrators, principals, superintendents | School news, budget info, technology initiatives |
| **Real Estate** | Recent homebuyers, property owners | Property data, neighborhood stats, market trends |
| **PAC** | Political donors, contributors | Contribution history, policy interests, news |

## Workflow

1.  **Ingestion**: CSV files placed in `leads/{pipeline}/` directory
2.  **Routing**: `PipelineRouter` classifies leads based on column headers
3.  **Enrichment**: `SerperClient` gathers personalization data for each lead
4.  **Generation**: `EmailGenerator` creates personalized content via OpenAI
5.  **Sending**: `InboxRotator` selects optimal inbox, `MailreefClient` sends email
6.  **Warming**: `WarmingOrchestrator` maintains inbox reputation via Smartlead

## Email Sequences

All campaigns use a 3-email sequence with timed intervals:
- Email 1: Day 0 (Initial outreach)
- Email 2: Day 4 (Follow-up with new information)
- Email 3: Day 11 (Final touch, low pressure)

## Volume Configuration

- Total sending capacity: 66,000 emails/month (active)
- Total warming capacity: 33,000 emails/month
- Inbox count: 200 distributed across campaigns
- Daily send limit: ~2,200 emails/day (active)

## Directory Structure

```
├── config.py                      # Central configuration
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Container configuration
├── pipeline.py                    # Main entry point
├── pipeline/
│   ├── router.py                  # Lead routing logic
│   └── campaign_orchestrator.py   # Sequence management
├── senders/
│   ├── mailreef_client.py         # Mailreef API integration
│   └── inbox_rotator.py           # Inbox rotation logic
├── generators/
│   └── email_generator.py         # OpenAI email generation
├── warming/
│   ├── smartlead_client.py        # Smartlead API integration
│   └── warming_orchestrator.py    # Warming campaign management
├── templates/
│   ├── school/
│   ├── real_estate/
│   └── pac/
├── leads/
│   ├── school/
│   ├── real_estate/
│   └── pac/
└── data/
    ├── cache/
    └── logs/
```

## Usage

```bash
# Run a campaign
python pipeline.py --campaign school --input leads/school/input.csv
python pipeline.py --campaign real_estate --input leads/real_estate/input.csv
python pipeline.py --campaign pac --input leads/pac/input.csv

# Run inbox warming
python pipeline.py --warming
```

```

---

## Environment Template
**File:** `.env.example`

```text
# OmniBot Cold Email Platform - Environment Variables
# Copy this file to .env and fill in your actual keys

# API Keys (Required)
OPENAI_API_KEY=your_openai_key_here
SERPER_API_KEY=your_serper_key_here
MAILREEF_API_KEY=your_mailreef_key_here
SMARTLEAD_API_KEY=your_smartlead_key_here

# Optional Configuration
DAILY_SEND_LIMIT=100
RATE_LIMIT=1.0
PROMETHEUS_PORT=8000
TOTAL_INBOXES=200
MONTHLY_ACTIVE_EMAIL_LIMIT=66000
MONTHLY_WARMING_EMAIL_LIMIT=33000

```

---

## Configuration
**File:** `config.py`

```python
import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Config:
    """Central configuration for OmniBot Platform."""
    
    # API Keys (from environment)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MAILREEF_API_KEY = os.getenv("MAILREEF_API_KEY")
    SMARTLEAD_API_KEY = os.getenv("SMARTLEAD_API_KEY")
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")  # Corrected from SERPAPI
    
    # Campaign Settings
    DAILY_SEND_LIMIT = int(os.getenv("DAILY_SEND_LIMIT", 100))
    RATE_LIMIT = float(os.getenv("RATE_LIMIT", 1.0))
    TIMEOUT = int(os.getenv("TIMEOUT", 30))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))

    # Monitoring
    PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", 8000))

    # Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    CACHE_DIR = os.path.join(DATA_DIR, "cache")
    LOGS_DIR = os.path.join(DATA_DIR, "logs")
    
    # Pipeline-specific directories
    LEADS_DIR = os.path.join(BASE_DIR, "leads")
    SCHOOL_LEADS_DIR = os.path.join(LEADS_DIR, "school")
    REAL_ESTATE_LEADS_DIR = os.path.join(LEADS_DIR, "real_estate")
    PAC_LEADS_DIR = os.path.join(LEADS_DIR, "pac")
    
    TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

    @classmethod
    def validate(cls):
        """Validates critical configuration presence."""
        missing = []
        if not cls.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        if not cls.SERPER_API_KEY:
            missing.append("SERPER_API_KEY")
        
        # Create directories if they don't exist
        for directory in [
            cls.DATA_DIR, cls.CACHE_DIR, cls.LOGS_DIR, cls.LEADS_DIR,
            cls.SCHOOL_LEADS_DIR, cls.REAL_ESTATE_LEADS_DIR, cls.PAC_LEADS_DIR,
            cls.TEMPLATES_DIR
        ]:
            os.makedirs(directory, exist_ok=True)

        if missing:
            logger.warning(f"Missing configuration keys: {', '.join(missing)}")

    @classmethod
    def get_secret(cls, key: str) -> Optional[str]:
        """Retrieves a secret from environment."""
        return os.getenv(key)


class PipelineConfig:
    """Pipeline-specific settings."""
    
    # Volume Configuration
    MONTHLY_ACTIVE_EMAIL_LIMIT = int(os.getenv("MONTHLY_ACTIVE_EMAIL_LIMIT", 66000))
    MONTHLY_WARMING_EMAIL_LIMIT = int(os.getenv("MONTHLY_WARMING_EMAIL_LIMIT", 33000))
    
    # Distribution across 3 campaigns
    SCHOOL_CAMPAIGN_ALLOCATION = 0.33
    REAL_ESTATE_CAMPAIGN_ALLOCATION = 0.33
    PAC_CAMPAIGN_ALLOCATION = 0.34
    
    # Inbox Configuration
    TOTAL_INBOXES = int(os.getenv("TOTAL_INBOXES", 200))
    INBOXES_PER_CAMPAIGN = TOTAL_INBOXES // 3
    
    # Email Sequence Configuration
    EMAILS_PER_SEQUENCE = 3
    SEQUENCE_DAYS_BETWEEN_EMAILS = [0, 4, 11]  # Day 0, Day 4, Day 11

```

---

## Requirements
**File:** `requirements.txt`

```text
openai
python-dotenv
dataclasses-json
prometheus-client
tenacity
jsonschema
pandas
pytest
pytest-asyncio
requests
python-dateutil

```

---

## Main Entry Point
**File:** `pipeline.py`

```python
#!/usr/bin/env python3
"""
OmniBot Cold Email Platform - Main Entry Point

Usage:
    python pipeline.py --campaign school --input leads/school/input.csv
    python pipeline.py --campaign real_estate --input leads/real_estate/input.csv
    python pipeline.py --campaign pac --input leads/pac/input.csv
    python pipeline.py --warming
"""

import argparse
import logging
import sys
import pandas as pd
from datetime import datetime

# Import internal modules
from config import Config, PipelineConfig
from pipeline.router import PipelineRouter
from pipeline.campaign_orchestrator import CampaignOrchestrator
from senders.mailreef_client import MailreefClient
from senders.inbox_rotator import InboxRotator
from generators.email_generator import EmailGenerator
from warming.warming_orchestrator import WarmingOrchestrator
from warming.smartlead_client import SmartleadClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_campaign(campaign_type: str, input_csv: str):
    """
    Execute a complete campaign run.
    """
    logger.info(f"Starting {campaign_type} campaign with input: {input_csv}")

    # Initialize components
    Config.validate()

    mailreef_client = MailreefClient()
    inbox_rotator = InboxRotator(mailreef_client, PipelineConfig)
    inbox_rotator.refresh_pool()

    email_generator = EmailGenerator()
    orchestrator = CampaignOrchestrator(campaign_type, PipelineConfig)

    # Load leads
    try:
        leads_df = pd.read_csv(input_csv)
        logger.info(f"Loaded {len(leads_df)} leads")
    except Exception as e:
        logger.error(f"Failed to load input CSV: {e}")
        return {"sent": 0, "failed": 0, "error": str(e)}

    # Process leads to determine who needs emails
    processing_result = orchestrator.process_leads(leads_df)
    ready_leads = processing_result["ready_to_send"]

    logger.info(f"Leads ready to send: {len(ready_leads)}")

    # Process each lead
    sent_count = 0
    failed_count = 0

    for lead_info in ready_leads:
        lead = lead_info["lead"]
        sequence_num = lead_info["sequence_number"]

        # Select inbox
        inbox = inbox_rotator.select_inbox(campaign_type)
        if not inbox:
            logger.warning("No healthy inboxes available, deferring send")
            break

        # Generate email
        email_content = email_generator.generate_email(
            campaign_type=campaign_type,
            sequence_number=sequence_num,
            lead_data=lead.to_dict() if hasattr(lead, 'to_dict') else dict(lead),
            enrichment_data=lead.get("enrichment_data", {}) if isinstance(lead, dict) else {}
        )

        # Send email
        to_email = lead.get("email", lead.get("Email", ""))
        if not to_email:
            logger.warning(f"No email address for lead, skipping")
            failed_count += 1
            continue

        result = mailreef_client.send_email(
            inbox_id=inbox.id,
            to=to_email,
            subject=email_content["subject"],
            body=email_content["body"]
        )

        if result.get("success"):
            sent_count += 1
            logger.info(f"Sent email {sequence_num} to {to_email}")
        else:
            failed_count += 1
            logger.error(f"Failed to send to {to_email}: {result.get('error')}")

    logger.info(f"Campaign complete. Sent: {sent_count}, Failed: {failed_count}")

    return {"sent": sent_count, "failed": failed_count}


def run_warming():
    """
    Execute inbox warming operations.
    """
    logger.info("Starting inbox warming operations")

    Config.validate()

    smartlead_client = SmartleadClient()
    mailreef_client = MailreefClient()
    inbox_rotator = InboxRotator(mailreef_client, PipelineConfig)

    warming_orchestrator = WarmingOrchestrator(smartlead_client, inbox_rotator, PipelineConfig)

    # Assign or update warming campaigns
    campaign = warming_orchestrator.assign_warming_campaigns()

    if campaign and not campaign.get("error"):
        logger.info(f"Warming campaign created/updated: {campaign.get('id', 'N/A')}")
    else:
        logger.warning(f"Warming campaign issue: {campaign}")

    # Monitor progress
    progress = warming_orchestrator.monitor_warming_progress()
    logger.info(f"Warming progress: {progress}")

    return progress


def main():
    parser = argparse.ArgumentParser(description="OmniBot Cold Email Platform")
    parser.add_argument(
        "--campaign",
        choices=["school", "real_estate", "pac"],
        help="Campaign type to run"
    )
    parser.add_argument(
        "--input",
        help="Path to input CSV file with leads"
    )
    parser.add_argument(
        "--warming",
        action="store_true",
        help="Run inbox warming operations"
    )

    args = parser.parse_args()

    if args.warming:
        run_warming()
    elif args.campaign and args.input:
        run_campaign(args.campaign, args.input)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

```

---

## Dockerfile
**File:** `Dockerfile`

```dockerfile

# Multi-stage build for specialized production image
FROM python:3.9-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.9-slim
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Configuration defaults
ENV PROMETHEUS_PORT=8000
ENV DAILY_SEND_LIMIT=100
ENV PYTHONUNBUFFERED=1

# Expose metrics port
EXPOSE 8000

# Health check (Generic check if script is runnable, or hit metrics port)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/ || exit 1

# Entrypoint
ENTRYPOINT ["python", "pipeline.py"]
CMD ["input_websites.csv"]

```

---

## Pipeline Router
**File:** `pipeline/router.py`

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict
import pandas as pd


@dataclass
class Lead:
    """Standardized lead format across all pipelines."""
    source_data: dict
    email: str
    first_name: str
    last_name: str
    company: str
    enrichment_data: dict = field(default_factory=dict)
    generated_emails: list = field(default_factory=list)
    status: str = "pending"


class PipelineRouter:
    """
    Routes leads to the appropriate campaign based on input columns.
    """

    PIPELINE_DETECTORS = {
        "school": ["school_name", "district", "principal", "superintendent", "school_admin", "website"],
        "real_estate": ["property_address", "purchase_date", "home_value", "buyer_name", "owner_name"],
        "pac": ["donor", "contribution_amount", "political_affiliation", "donation_date", "contributor_name"]
    }

    def classify_lead(self, df: pd.DataFrame) -> str:
        """
        Determine pipeline based on DataFrame columns.
        """
        columns = [col.lower().replace(" ", "_") for col in df.columns]

        for pipeline, identifiers in self.PIPELINE_DETECTORS.items():
            if any(ident in columns for ident in identifiers):
                return pipeline

        return "school"  # Default fallback

    def route(self, csv_path: str) -> str:
        """
        Route a CSV file to its appropriate pipeline.
        """
        df = pd.read_csv(csv_path)
        return self.classify_lead(df)

```

---

## Campaign Orchestrator
**File:** `pipeline/campaign_orchestrator.py`

```python
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

```

---

## Mailreef Client
**File:** `senders/mailreef_client.py`

```python
import os
import requests
import logging
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

MAILREEF_API_KEY = os.getenv("MAILREEF_API_KEY")
MAILREEF_BASE_URL = "https://api.mailreef.io/v1"

logger = logging.getLogger(__name__)


class MailreefClient:
    """
    Client for Mailreef email sending infrastructure.
    """

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {MAILREEF_API_KEY}",
            "Content-Type": "application/json"
        }

    def get_inboxes(self) -> List[Dict]:
        """
        Retrieve all available inboxes.
        """
        try:
            response = requests.get(f"{MAILREEF_BASE_URL}/inboxes", headers=self.headers)
            response.raise_for_status()
            return response.json().get("inboxes", [])
        except requests.RequestException as e:
            logger.error(f"Mailreef API Error (get_inboxes): {e}")
            return []

    def get_inbox_status(self, inbox_id: str) -> Dict:
        """
        Check the status and health of a specific inbox.
        """
        try:
            response = requests.get(f"{MAILREEF_BASE_URL}/inboxes/{inbox_id}", headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Mailreef API Error (get_inbox_status): {e}")
            return {}

    def send_email(self, inbox_id: str, to: str, subject: str, body: str) -> Dict:
        """
        Send a single email through the specified inbox.
        """
        payload = {
            "to": to,
            "subject": subject,
            "html": body
        }
        try:
            response = requests.post(
                f"{MAILREEF_BASE_URL}/inboxes/{inbox_id}/send",
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.RequestException as e:
            logger.error(f"Mailreef API Error (send_email): {e}")
            return {"success": False, "error": str(e)}

    def get_daily_quota(self, inbox_id: str) -> int:
        """
        Get remaining daily sending quota for an inbox.
        """
        status = self.get_inbox_status(inbox_id)
        return status.get("daily_quota_remaining", 0)

```

---

## Inbox Rotator
**File:** `senders/inbox_rotator.py`

```python
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

```

---

## Email Generator
**File:** `generators/email_generator.py`

```python
import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class EmailGenerator:
    """
    Generates hyper-personalized email content using OpenAI.
    """

    CAMPAIGN_PROMPTS = {
        "school": {
            "email_1": """You are Andrew, a cold outreach specialist working with school districts.
Generate a personalized outreach email for {first_name} at {school_name}.

Context from research:
{enrichment_data}

Requirements:
- Subject line: Direct and curiosity-driven
- Body: 3-4 paragraphs, conversational tone
- Personalization: Reference specific details from research
- CTA: Soft, low-pressure invitation to conversation
- Length: Under 150 words
- Style: Professional but warm, not salesy

Output format:
SUBJECT: [subject line here]
BODY: [email body here]
""",
            "email_2": """You are Andrew, following up on a cold outreach email.
Generate a follow-up email for {first_name} at {school_name}.

Context from research:
{enrichment_data}

Original first email topic: {original_topic}

Requirements:
- Acknowledge previous email without being pushy
- Add new piece of information or angle
- Keep it brief and valuable
- Length: Under 100 words
- Style: Respectful of their time

Output format:
SUBJECT: [subject line here]
BODY: [email body here]
""",
            "email_3": """You are Andrew, sending a final follow-up email.
Generate a closing email for {first_name} at {school_name}.

Context from research:
{enrichment_data}

Requirements:
- Final touch in sequence
- Leave the door open for future connection
- No pressure tactics
- Length: Under 80 words
- Style: Gracious and professional

Output format:
SUBJECT: [subject line here]
BODY: [email body here]
"""
        },
        "real_estate": {
            "email_1": """You are Andrew from Aspire Realty, reaching out to a recent homebuyer.
Generate a personalized outreach email for {first_name} who recently purchased a property.

Context from research:
{enrichment_data}

Requirements:
- Subject line: Reference their property or neighborhood
- Body: 3-4 paragraphs, neighbor-friendly tone
- Personalization: Reference property details like year built, type
- CTA: Offer to be a local resource
- Length: Under 150 words
- Style: Warm, neighborly, helpful

Output format:
SUBJECT: [subject line here]
BODY: [email body here]
""",
            "email_2": """You are Andrew from Aspire Realty, following up with a homeowner.
Generate a follow-up email for {first_name}.

Context from research:
{enrichment_data}

Requirements:
- Offer value: maintenance tips, local insights
- Keep it brief
- Length: Under 100 words

Output format:
SUBJECT: [subject line here]
BODY: [email body here]
""",
            "email_3": """You are Andrew from Aspire Realty, sending a final friendly check-in.
Generate a closing email for {first_name}.

Requirements:
- Final touch, no pressure
- Leave door open
- Length: Under 80 words

Output format:
SUBJECT: [subject line here]
BODY: [email body here]
"""
        },
        "pac": {
            "email_1": """You are Mark Greenstein, reaching out to a politically engaged professional.
Generate a personalized outreach email for {first_name} at {company}.

Context from research:
{enrichment_data}

Requirements:
- Subject line: Reference their civic engagement or industry
- Body: 3-4 paragraphs, peer-to-peer professional tone
- Personalization: Acknowledge their contributions without naming amounts
- CTA: Invite to a conversation about shared interests
- Length: Under 150 words
- Style: Deferential, professional, politically neutral

Output format:
SUBJECT: [subject line here]
BODY: [email body here]
""",
            "email_2": """You are Mark Greenstein, following up with a professional donor.
Generate a follow-up email for {first_name} at {company}.

Context from research:
{enrichment_data}

Requirements:
- Bridge political interest to business context
- Keep it professional
- Length: Under 100 words

Output format:
SUBJECT: [subject line here]
BODY: [email body here]
""",
            "email_3": """You are Mark Greenstein, sending a final professional note.
Generate a closing email for {first_name}.

Requirements:
- Final touch, professional
- Leave door open for future
- Length: Under 80 words

Output format:
SUBJECT: [subject line here]
BODY: [email body here]
"""
        }
    }

    def __init__(self, client=None):
        self.client = client or openai_client

    def generate_email(
        self,
        campaign_type: str,
        sequence_number: int,
        lead_data: dict,
        enrichment_data: dict
    ) -> dict:
        """
        Generate a single email based on campaign type and sequence position.
        """
        prompt_key = f"email_{sequence_number}"
        prompt_template = self.CAMPAIGN_PROMPTS.get(campaign_type, {}).get(prompt_key)
        
        if not prompt_template:
            logger.error(f"No prompt found for {campaign_type} / {prompt_key}")
            return {"subject": "Error", "body": "Prompt not found"}

        # Format enrichment data for prompt
        enrichment_text = self._format_enrichment(enrichment_data)

        # Construct prompt with all variables
        prompt = prompt_template.format(
            first_name=lead_data.get("first_name", lead_data.get("name", "there")),
            school_name=lead_data.get("school_name", lead_data.get("company", "")),
            company=lead_data.get("company", lead_data.get("employer", "")),
            enrichment_data=enrichment_text,
            original_topic=lead_data.get("last_email_topic", "our previous discussion")
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )

            # Parse response
            content = response.choices[0].message.content
            return self._parse_response(content)
        except Exception as e:
            logger.error(f"OpenAI API Error: {e}")
            return {"subject": "Error", "body": f"Generation failed: {e}"}

    def _format_enrichment(self, data: dict) -> str:
        """
        Format enrichment data into a readable string for the prompt.
        """
        if not data:
            return "No additional research data available."

        lines = []
        for key, value in data.items():
            if value and key not in ["email", "phone", "website"]:
                lines.append(f"- {key.replace('_', ' ').title()}: {value}")

        return "\n".join(lines) if lines else "No additional research data available."

    def _parse_response(self, content: str) -> dict:
        """
        Parse the raw LLM response into structured email data.
        """
        lines = content.strip().split("\n")
        subject = ""
        body_lines = []

        current_section = None
        for line in lines:
            if line.startswith("SUBJECT:"):
                current_section = "subject"
                subject = line.replace("SUBJECT:", "").strip()
            elif line.startswith("BODY:"):
                current_section = "body"
                body_lines.append(line.replace("BODY:", "").strip())
            elif current_section == "body":
                body_lines.append(line)

        return {
            "subject": subject,
            "body": "\n".join(body_lines).strip()
        }

```

---

## Smartlead Client
**File:** `warming/smartlead_client.py`

```python
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

```

---

## Warming Orchestrator
**File:** `warming/warming_orchestrator.py`

```python
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

```

---

## School Template 1
**File:** `templates/school/email_1.txt`

```text
Subject: Quick question about {{ school_name }}

Hi {{ first_name }},

I noticed that {{ school_name }} has been {{ recent_development }}. As someone who works with school districts across {{ state }}, I'm curious—how are you handling {{ challenge_area }} this year?

I've helped districts like {{ comparable_district }} achieve {{ specific_outcome }}. Would you be open to a brief conversation about what's working for {{ school_name }}?

Best,
Andrew

```

---

## School Template 2
**File:** `templates/school/email_2.txt`

```text
Subject: Re: Quick question about {{ school_name }}

Hi {{ first_name }},

Following up on my previous message—since we last connected, {{ school_name }} has {{ new_development }}. This seems like it could impact {{ specific_area }}.

I'd love to share how we've helped similar districts navigate {{ related_challenge }}. Are you the right person to discuss {{ topic }}, or would you point me to someone on your team?

No pressure if now isn't a good time.

Best,
Andrew

```

---

## School Template 3
**File:** `templates/school/email_3.txt`

```text
Subject: Last attempt - {{ school_name }} and {{ topic }}

Hi {{ first_name }},

I'll make this quick. I've been reaching out because {{ school_name }} seems like a great fit for what we do—helping districts with {{ core_benefit }}.

I understand you're busy, so I'll leave it here. If you ever want to explore how we can help with {{ current_initiative }}, feel free to reach out.

Best,
Andrew

```

---

## Real Estate Template 1
**File:** `templates/real_estate/email_1.txt`

```text
Subject: Quick question about {{ property_address }}

Hi {{ first_name }},

I noticed you recently moved into {{ property_address }}—congratulations on the purchase! The {{ property_type }} looks like it was built around {{ built_year }}, which means it's got some great character.

I work with homeowners in the {{ neighborhood }} area and wanted to introduce myself. If you ever need recommendations for local services or have questions about the area, I'm happy to help.

Welcome to the neighborhood!

Best,
Andrew
Aspire Realty

```

---

## Real Estate Template 2
**File:** `templates/real_estate/email_2.txt`

```text
Subject: Maintenance tip for {{ property_type }} owners

Hi {{ first_name }},

Properties built in {{ built_year }} often have specific maintenance considerations around this time of year—especially for {{ maintenance_area }}.

I put together a quick guide for homeowners in your situation. Would you find that helpful?

Best,
Andrew
Aspire Realty

```

---

## Real Estate Template 3
**File:** `templates/real_estate/email_3.txt`

```text
Subject: One last note

Hi {{ first_name }},

Just wanted to check in one more time. I know settling into a new home keeps you busy.

If you ever need anything real estate related—whether it's a contractor recommendation or market questions—don't hesitate to reach out.

Best,
Andrew
Aspire Realty

```

---

## PAC Template 1
**File:** `templates/pac/email_1.txt`

```text
Subject: Your support for {{ recipient }}

Hi {{ first_name }},

I noticed your consistent support for {{ recipient }} and the {{ industry }} sector. It's rare to see such dedicated civic engagement.

As someone who works with professionals in the {{ industry }} space, I'm curious about your perspective on {{ policy_topic }}. Would you be open to a brief conversation?

Best,
Mark Greenstein

```

---

## PAC Template 2
**File:** `templates/pac/email_2.txt`

```text
Subject: Intersection of {{ industry }} and policy

Hi {{ first_name }},

Given your role at {{ company }}, I thought you'd be interested in how policy shifts are affecting the {{ industry }} landscape.

I've been tracking {{ specific_development }} and its implications for businesses like yours. Would love to share some insights if you're interested.

Best,
Mark Greenstein

```

---

## PAC Template 3
**File:** `templates/pac/email_3.txt`

```text
Subject: Quick note

Hi {{ first_name }},

I'll keep this brief. If you're ever interested in discussing how policy developments are affecting the {{ industry }} sector, I'd welcome the conversation.

No agenda—just peer-to-peer knowledge sharing.

Best,
Mark Greenstein

```

---

## Serper Enricher
**File:** `Jobs/researcher/serp_enricher.py`

```python
"""
Serper Data Enrichment Module

This module uses Serper API exclusively for lead enrichment.
All custom scraping logic has been removed per the Production Readiness Action Plan.
"""

import os
import requests
import logging
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
SERPER_BASE_URL = "https://google.serper.dev"

logger = logging.getLogger(__name__)


def serper_search(query: str, engine: str = "search") -> Dict:
    """
    Execute search via Serper API.
    
    Args:
        query: Search query string
        engine: Search engine type (search, news, images, places)
    
    Returns:
        JSON response from Serper API
    """
    if not SERPER_API_KEY:
        logger.error("SERPER_API_KEY not configured")
        return {}
    
    url = f"{SERPER_BASE_URL}/{engine}"
    payload = {"q": query}
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Serper API Error: {e}")
        return {}


def serper_company_search(company_name: str) -> Dict:
    """
    Search for company information using Serper.
    
    Args:
        company_name: Name of the company to search
    
    Returns:
        Enrichment data dict with company info
    """
    result = serper_search(f"{company_name} company information")
    
    enrichment = {
        "company_name": company_name,
        "description": "",
        "website": "",
        "industry": ""
    }
    
    if result.get("organic"):
        first_result = result["organic"][0]
        enrichment["description"] = first_result.get("snippet", "")
        enrichment["website"] = first_result.get("link", "")
    
    if result.get("knowledgeGraph"):
        kg = result["knowledgeGraph"]
        enrichment["description"] = kg.get("description", enrichment["description"])
        enrichment["industry"] = kg.get("type", "")
    
    return enrichment


def serper_news_search(entity_name: str, days_back: int = 30) -> List[Dict]:
    """
    Search for recent news about an entity.
    
    Args:
        entity_name: Name of person/company to search news for
        days_back: Number of days to look back (affects query phrasing)
    
    Returns:
        List of news items with title, snippet, and link
    """
    query = f"{entity_name} news recent"
    result = serper_search(query, engine="news")
    
    news_items = []
    for item in result.get("news", [])[:5]:
        news_items.append({
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
            "link": item.get("link", ""),
            "date": item.get("date", "")
        })
    
    return news_items


def serper_school_search(school_name: str, district: str = "") -> Dict:
    """
    Search for school/district information.
    
    Args:
        school_name: Name of the school
        district: Optional district name
    
    Returns:
        Enrichment data dict with school info
    """
    query = f"{school_name} {district} school district initiatives news".strip()
    result = serper_search(query)
    
    enrichment = {
        "school_name": school_name,
        "district": district,
        "recent_initiatives": "",
        "news_summary": ""
    }
    
    # Extract from organic results
    if result.get("organic"):
        snippets = [r.get("snippet", "") for r in result["organic"][:3]]
        enrichment["recent_initiatives"] = " | ".join(snippets)
    
    # Get news
    news = serper_news_search(f"{school_name} {district}".strip())
    if news:
        enrichment["news_summary"] = news[0].get("title", "")
    
    return enrichment


def serper_property_search(address: str) -> Dict:
    """
    Search for property information.
    
    Args:
        address: Property address
    
    Returns:
        Enrichment data dict with property info
    """
    query = f"{address} property details zillow redfin"
    result = serper_search(query)
    
    enrichment = {
        "address": address,
        "built_year": "",
        "property_type": "Single Family",
        "neighborhood": ""
    }
    
    # Try to extract year built from snippets
    if result.get("organic"):
        for r in result["organic"]:
            snippet = r.get("snippet", "").lower()
            # Simple year extraction
            import re
            year_match = re.search(r"built in (\d{4})", snippet)
            if year_match:
                enrichment["built_year"] = year_match.group(1)
                break
            
            # Property type detection
            if "condo" in snippet:
                enrichment["property_type"] = "Condo"
            elif "townhouse" in snippet or "townhome" in snippet:
                enrichment["property_type"] = "Townhouse"
    
    return enrichment


def serper_donor_search(donor_name: str, employer: str = "") -> Dict:
    """
    Search for information about a political donor.
    
    Args:
        donor_name: Name of the donor
        employer: Optional employer name
    
    Returns:
        Enrichment data dict with donor/professional info
    """
    query = f"{donor_name} {employer} professional business".strip()
    result = serper_search(query)
    
    enrichment = {
        "name": donor_name,
        "employer": employer,
        "industry": "Business",
        "professional_context": ""
    }
    
    if result.get("organic"):
        first = result["organic"][0]
        enrichment["professional_context"] = first.get("snippet", "")
    
    # Try to infer industry from results
    if result.get("organic"):
        combined = " ".join([r.get("snippet", "") for r in result["organic"][:3]]).lower()
        
        if "tech" in combined or "software" in combined:
            enrichment["industry"] = "Technology"
        elif "finance" in combined or "bank" in combined or "investment" in combined:
            enrichment["industry"] = "Finance"
        elif "health" in combined or "medical" in combined or "pharma" in combined:
            enrichment["industry"] = "Healthcare"
        elif "real estate" in combined or "property" in combined:
            enrichment["industry"] = "Real Estate"
        elif "energy" in combined or "oil" in combined:
            enrichment["industry"] = "Energy"
    
    # Get news about employer
    if employer:
        news = serper_news_search(employer)
        if news:
            enrichment["employer_news"] = news[0].get("title", "")
    
    return enrichment


def enrich_lead(lead: Dict, campaign_type: str) -> Dict:
    """
    Main enrichment function that routes to campaign-specific enrichment.
    
    Args:
        lead: Lead data dictionary
        campaign_type: One of 'school', 'real_estate', 'pac'
    
    Returns:
        Enriched lead data
    """
    if campaign_type == "school":
        school_name = lead.get("school_name", lead.get("School Name", ""))
        district = lead.get("district", lead.get("District", ""))
        return serper_school_search(school_name, district)
    
    elif campaign_type == "real_estate":
        address = lead.get("property_address", lead.get("Property Address", ""))
        return serper_property_search(address)
    
    elif campaign_type == "pac":
        name = lead.get("contributor_name", lead.get("Contributor Name", lead.get("name", "")))
        employer = lead.get("employer", lead.get("Employer", ""))
        return serper_donor_search(name, employer)
    
    else:
        logger.warning(f"Unknown campaign type: {campaign_type}")
        return {}

```

---

