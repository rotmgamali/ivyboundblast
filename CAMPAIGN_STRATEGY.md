# Private School Email Campaign Strategy

**Target**: Private schools in Florida  
**Sequence**: 2 emails (Day 0, Day 4)  
**Monthly Volume**: 50,000 emails

---

## Strategy Overview

### Email 1 (Day 0) - Door Opener
- **Goal**: Get them to open, read, and RESPOND (start a conversation)
- **Tone**: Personal, curious, friendly—not salesy
- **Approach**: Ask about THEIR situation, learn from them
- **Personalization**: Use `{{ school_name }}`, `{{ program_emphasis }}` from homepage scrape, and Florida regional context
- **Length**: Under 100 words
- **No stats, no pitch deck, no heavy data**

### Email 2 (Day 4) - Curiosity Builder
- **Goal**: Get them curious enough to take a 15-minute call/Zoom
- **Tone**: Helpful, data-backed, low-pressure
- **Approach**: Share proof points, pitch deck link, specific pricing
- **Personalization**: Reference the school, offer ready-made materials
- **Include**: All verified stats, package pricing, pitch deck URL
- **Ask**: "Would 15 minutes be helpful?"

---

## Business Model

**We sell to STUDENTS/FAMILIES. Schools help us DISTRIBUTE.**

Schools are distribution partners, not customers. We ask them to:
- Share flyers in counseling offices
- Include us in parent newsletters
- Host free Parent Education Nights
- Mention during advising sessions

**Zero cost to school. Zero admin burden. Parents sign up directly with us.**

---

## Decision Maker Segments

### 1. Head of School
| Attribute | Value |
|-----------|-------|
| Template Folder | `head_of_school/` |
| Sender | Mark Greenstein |
| Email 2 Pitch Deck | [ibforschools.info](https://ibforschools.info/) |
| Focus | Premium differentiation, tuition justification, college outcomes |
| Role Keywords | head of school, headmaster, headmistress, superintendent, executive director |

---

### 2. Principal
| Attribute | Value |
|-----------|-------|
| Template Folder | `principal/` |
| Sender | Andrew |
| Email 2 Pitch Deck | [ibschooldiscounts.info](https://ibschooldiscounts.info/) |
| Focus | Parent satisfaction, easy value-add, no admin burden |
| Role Keywords | principal, assistant principal, vice principal |

---

### 3. Academic Dean
| Attribute | Value |
|-----------|-------|
| Template Folder | `academic_dean/` |
| Sender | Genelle |
| Email 2 Pitch Deck | [ibschooldiscounts.info](https://ibschooldiscounts.info/) |
| Focus | Academic outcomes, test prep workshops, curriculum enhancement |
| Role Keywords | academic dean, dean of academics, curriculum director, director of academics, dean of studies |

---

### 4. Director of College Counseling
| Attribute | Value |
|-----------|-------|
| Template Folder | `college_counseling/` |
| Sender | Andrew |
| Email 2 Pitch Deck | [ibschooldiscounts.info](https://ibschooldiscounts.info/) |
| Focus | Test prep recommendations, merit scholarships, college admissions |
| Role Keywords | college counselor, college counseling, director of college counseling, guidance director, guidance counselor |

---

### 5. Business Manager / CFO
| Attribute | Value |
|-----------|-------|
| Template Folder | `business_manager/` |
| Sender | Mark Greenstein |
| Email 2 Pitch Deck | [ibschooldiscounts.info](https://ibschooldiscounts.info/) |
| Focus | Zero cost, tuition justification, value-add for families |
| Role Keywords | business manager, cfo, chief financial, director of finance, business office |

---

### 6. General (Unknown Titles)
| Attribute | Value |
|-----------|-------|
| Template Folder | `general/` |
| Sender | Mark Greenstein |
| Fallback for any unrecognized role titles |

---

## Personalization Variables

| Variable | Source | Example |
|----------|--------|---------|
| `{{ first_name }}` | Lead spreadsheet | "Sarah" |
| `{{ school_name }}` | Lead spreadsheet or scraped | "Saint Andrews Academy" |
| `{{ program_emphasis }}` | Scraped from homepage | "STEM", "Arts", "College Prep", "International" |

---

## Verified Claims (Playbook-Approved)

Only use these statistics—they are verified:

### Track Record
| Metric | Value |
|--------|-------|
| Students Helped | 10,000+ |
| SAT Point Increase (Average) | 150+ points |
| ACT Section Points Increase | 14.2+ points |
| Merit Awards Won (Average) | $125,000+ |
| Return on Investment | 6,000% average |
| Years in Business | 25 |
| School Partners | 50+ |

### Score Guarantee
- 100+ point score increase guarantee
- 50% refund if target not met

### Package Pricing
| Package | Price | Retail | Discount |
|---------|-------|--------|----------|
| Essentials | $375 | $850 | 56% off |
| Premier | $675 | $1,350 | 50% off |

### Essentials Package Includes
- 18-20 hours live instruction
- 50+ practice tests
- 4+ full mock exams

### Premier Package Includes
- 28-30 hours live instruction
- 2 hours private tutoring
- 50+ practice tests
- 6+ full mock exams

---

## Low-Friction Entry Points (From Playbook)

Offer these in Email 2 to make it easy to say yes:

- **Free Parent Education Night**: We run it, school just provides the room
- **1-Hour Workshops**: Test readiness, study skills—during advisory or college prep weeks
- **Sample Materials**: Flyers, newsletter copy, digital assets ready to share
- **15-Minute Call**: Quick walkthrough of how other Florida schools use this

---

## Email Tone Guidelines

From the playbook: **"If outreach feels like selling, it will fail."**

### Email 1 - DO:
- Reference their school and program emphasis
- Ask about THEIR situation (be curious)
- Keep it under 100 words
- End with a genuine question
- Use first name only in signature (not full credentials)

### Email 1 - DON'T:
- Include any stats or data
- Mention pricing
- Include pitch deck links
- Use "We offer..." language
- Make it about us

### Email 2 - DO:
- Include all relevant proof points
- Share specific pricing
- Include pitch deck link
- Ask for 15-minute call
- Offer ready-made materials

### Email 2 - DON'T:
- High-pressure language
- "Act now" urgency
- Claim things we can't verify

---

## Sending Schedule

| Day | Email | Goal |
|-----|-------|------|
| Day 0 | Email 1 | Start conversation (reply) |
| Day 4 | Email 2 | Book 15-minute call |

If no reply after Email 2, pause for 3-4 months before re-engaging.

---

## Template Files

```
templates/school/
├── head_of_school/
│   ├── email_1.txt  (door opener)
│   └── email_2.txt  (data + meeting ask)
├── principal/
│   ├── email_1.txt
│   └── email_2.txt
├── academic_dean/
│   ├── email_1.txt
│   └── email_2.txt
├── college_counseling/
│   ├── email_1.txt
│   └── email_2.txt
├── business_manager/
│   ├── email_1.txt
│   └── email_2.txt
└── general/
    ├── email_1.txt  (fallback for unknown roles)
    └── email_2.txt
```

---

## Handling Other Decision Maker Titles

When leads contain titles not in our mapping, they use the `general/` templates. As we identify additional common titles, we can:

1. Add them to the `ROLE_MAPPING` in `pipeline.py` to route to existing folders
2. Create new template folders if the role needs a distinct approach

Current approach: Route unknown titles to `general/` with Mark as sender.
