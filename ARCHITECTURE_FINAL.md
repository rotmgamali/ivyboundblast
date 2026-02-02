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
