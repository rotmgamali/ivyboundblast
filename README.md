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
