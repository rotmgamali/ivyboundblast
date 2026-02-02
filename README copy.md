# Ivy Bound School Partnership Campaign

Automated cold email outreach system for initiating academic partnerships with private schools.

## Overview

This campaign targets decision makers at private schools (K-12) across the United States, focusing on four key roles:

- **Heads of School / Superintendents** - Strategic partnerships generating $50,000-$150,000 in revenue
- **Academic Deans / Curriculum Directors** - Pedagogical alignment with Top 1% instructors
- **Business Managers / CFOs** - Cost savings of 50%+ on test prep programs
- **College Counseling Directors** - Enhanced student outcomes and scholarship opportunities

## Campaign Scale

- **Monthly Volume:** 50,000 emails
- **Target Response Rate:** 2-5%
- **Expected Monthly Partnerships:** 50-100

## Quick Start

### Installation

```bash
# Clone or navigate to campaign directory
cd campaign-directory

# Install dependencies
pip install -r requirements.txt

# Verify installation
python pipeline.py --help
```

### Basic Usage

```bash
# Test with a single domain
python pipeline.py --domain stmartins.edu --role principal

# Process leads file
python pipeline.py --input leads/school/input.csv --output enriched_leads.json

# Process with limited records
python pipeline.py --input leads.csv --max-records 100

# Skip scraping (use existing data)
python pipeline.py --input leads.csv --skip-scrape
```

### Pipeline Workflow

```
leads/school/input.csv
    ↓
[Lead Enrichment]
    ├─ Website scraping
    ├─ Data extraction
    └─ Personalization variables
    ↓
[Template Selection]
    ├─ Role detection
    ├─ Template matching
    └─ Variable injection
    ↓
enriched_leads.json
    ↓
[Email Platform Export]
```

## File Structure

```
campaign-directory/
├── pipeline.py              # Main orchestration script
├── scrape_school_data.py    # Website scraping module
├── requirements.txt         # Python dependencies
├── README.md               # This file
│
├── templates/school/       # Email templates by role
│   ├── superintendent/     # Head of School templates
│   │   ├── email_1.txt     # Revenue opportunity intro
│   │   └── email_2.txt     # Case study follow-up
│   │
│   ├── principal/          # Academic Dean templates
│   │   ├── email_1.txt     # Program enhancement
│   │   └── email_2.txt     # Implementation case study
│   │
│   ├── curriculum_director/
│   │   ├── email_1.txt     # Pedagogical quality
│   │   └── email_2.txt     # Standards alignment
│   │
│   └── federal_program_director/
│       ├── email_1.txt     # Compliance reduction
│       └── email_2.txt     # Documentation savings
│
├── leads/school/           # Lead data
│   ├── input.csv           # Raw leads
│   └── sample_leads.csv    # Example data
│
├── pitch_decks/            # External resources
│   ├── ibforschools.info   # Main partnership deck
│   ├── aaibcrossdistrict.info  # Cross-border revenue
│   ├── ibstemonstandby.info    # Emergency coverage
│   └── ibschooldiscounts.info  # Discounted programs
│
└── output/                 # Generated output
    └── (JSON files with enriched data)
```

## Template System

### Personalization Variables

All templates support dynamic personalization:

| Variable | Source | Example |
|----------|--------|---------|
| `{{ first_name }}` | Lead data | Jennifer |
| `{{ school_name }}` | Lead data | St. Mary's Academy |
| `{{ program_emphasis }}` | Website scrape | STEM Excellence |
| `{{ mission_statement }}` | Website scrape | Mission text... |
| `{{ recent_initiative }}` | Website scrape | New robotics lab |
| `{{ nearby_school }}` | Internal lookup | Brookfield Academy |

### Role Detection

The pipeline automatically maps roles to templates:

- `superintendent`, `head of school`, `headmaster` → `superintendent/`
- `principal`, `assistant principal` → `principal/`
- `curriculum director`, `academic dean` → `curriculum_director/`
- `federal program director`, `title i director` → `federal_program_director/`
- `college counselor`, `college counseling` → `college_counseling/`

### Sender Assignment

| Role | Sender |
|------|--------|
| Superintendent | Mark Greenstein |
| Principal | Andrew |
| Curriculum Director | Genelle |
| Federal Program Director | Mark Greenstein |
| College Counseling | Andrew |

## Website Scraping

### What Gets Scraped

The scraper extracts the following data points for personalization:

1. **Homepage Analysis**
   - School name and branding
   - Mission statement
   - Core values
   - Primary program emphasis

2. **Academic Pages**
   - Special programs
   - Curriculum approaches
   - Test preparation offerings

3. **College Counseling**
   - College outcomes claims
   - Counseling program descriptions

4. **News & Announcements**
   - Recent initiatives
   - Program launches
   - Achievement announcements

5. **Contact/Directory**
   - Email patterns
   - Key administrators
   - Head of School name

### Technical Implementation

```python
from scrape_school_data import SchoolWebsiteScraper

# Initialize scraper
scraper = SchoolWebsiteScraper()

# Scrape a single school
data = scraper.scrape("example.edu")

# Access scraped data
print(data.school_name)
print(data.program_emphasis)
print(data.mission_statement)
```

### Rate Limiting

The scraper includes automatic rate limiting:
- 1 second delay between requests
- 3 retry attempts per page
- Timeout: 10 seconds per request

## Email Sequences

### Sequence 1: Initial Outreach

**Purpose:** Introduce value proposition and generate interest

**Timing:** Day 0

**Content:**
- Personalized reference to school
- Core value proposition
- Relevant statistics or case study
- Low-friction CTA (reply to learn more)

### Sequence 2: Follow-up

**Purpose:** Provide social proof and overcome objections

**Timing:** Day 3-5 (if no response)

**Content:**
- Reference comparable school results
- Address common concerns
- Offer additional information
- Reiterate CTA

## Performance Metrics

### Target Benchmarks

| Metric | Target | Notes |
|--------|--------|-------|
| Deliverability | >95% | Clean lists, proper auth |
| Open Rate | >25% | Personalized subject lines |
| Click Rate | >3% | Relevant content |
| Reply Rate | 2-5% | Value-focused messaging |
| Meeting Conversion | 25% of replies | Follow-up process |
| Partnership Close | 10% of meetings | Sales execution |

### Financial Impact

| Metric | Target |
|--------|--------|
| Partnerships/Month | 50-100 |
| Revenue/Partnership | $10,000-50,000/year |
| CAC | <$100/partnership |
| LTV | $30,000-150,000 |

## Reply Handling

All replies route to: `andrew@web4guru.com`

### Response Priorities

| Priority | Response Time | Action |
|----------|---------------|--------|
| Hot (wants call) | < 1 hour | Schedule immediately |
| Warm (questions) | < 4 hours | Answer + next step |
| Cold (decline) | < 72 hours | Acknowledge, archive |
| Negative | Immediate | Remove, apologize |

## External Resources

### Pitch Decks

- **Main Partnership:** https://ibforschools.info/
- **Cross-Border Revenue:** https://aaibcrossdistrict.info/
- **STEM on Standby:** https://ibstemonstandby.info/
- **School Discounts:** https://ibschooldiscounts.info/

## Troubleshooting

### Common Issues

**Scraping failures:**
- Check domain format (use 'example.edu', not 'https://example.edu')
- Verify website is accessible
- Increase retry count in SchoolWebsiteScraper

**Template not found:**
- Check role spelling against ROLE_MAPPING
- Verify template files exist in correct directory
- Ensure template folder is readable

**Variable injection failures:**
- Check that all variables are properly formatted (`{{ var }}`)
- Verify variables exist in lead or scraped data
- Review logs for specific errors

### Debug Mode

Run with verbose logging:

```bash
python pipeline.py --input leads.csv 2>&1 | tee debug.log
```

## Compliance

### CAN-SPAM Requirements

- Physical address in all emails
- Clear opt-out mechanism
- Unsubscribe processing within 10 days
- Honest subject lines

### List Hygiene

- Remove bounces immediately
- Suppress unsubscribes for 2-3 years
- Regular list validation
- Engagement-based suppression

## Support

For questions about implementation or optimization, contact the campaign team.

---

**Campaign Version:** 1.0  
**Last Updated:** February 2025  
**Next Review:** April 2025
