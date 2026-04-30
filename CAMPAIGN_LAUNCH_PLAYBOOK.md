# Campaign Launch Playbook

Two campaigns are wired and ready to send. Both share the same compliance + safety stack (DMARC `p=reject`, CAN-SPAM footer, daily caps, opt-out enforcement, Smartlead warmup on all 168 inboxes).

---

## Campaign 1: IVYBOUND_SUMMER

**Pitch:** Schools share Ivybound's summer enrichment programs (SAT/ACT prep, AP review, executive function coaching) with their families — at zero cost and zero admin burden to the school.

**Server:** truckice (88 inboxes)
**Leads:** 10,076 pending in `Ivy Bound - Campaign Leads` sheet (verified, ready to send)
**Templates:** `templates/school_summer/{archetype}/email_{1,2}.txt` — 6 archetypes
**Sender:** Andrew Rollins, Mark Greenstein, or Genelle Carter — Ivybound Education Partners

### Launch Command
```bash
nohup /Users/mac/Ivybound/.venv/bin/python /Users/mac/Ivybound/mailreef_automation/main.py \
  --profile IVYBOUND_SUMMER >> /Users/mac/Ivybound/logs/ivybound_summer.log 2>&1 &
```

### Volume Ramp
| Week | Per-inbox/day | Daily total | Pace |
|---|---|---|---|
| 1 | 5 | 440 | ~9K/month |
| 2 | 10 | 880 | ~18K/month |
| 3 | 15 | 1,320 | ~27K/month |
| 4+ | 20 | 1,760 | ~36K/month |

Adjust `EMAILS_PER_INBOX_DAY_BUSINESS` in `automation_config.py` before each ramp step.

---

## Campaign 2: BAHAMAS_RETREAT

**Pitch:** Florida-area executives book corporate retreats / executive offsites at SerenitySpaces (private 4-villa complex in Freeport, Grand Bahama). 35-min flight from Fort Lauderdale, $150-$650/night.

**Server:** competitionhand (80 inboxes)
**Leads:** *Not yet harvested — must run scraper first*
**Templates:** `templates/bahamas/{archetype}/email_{1,2}.txt` — 4 archetypes (ceo_founder, coo_cfo, director, general)
**Sender:** Andrew, Mark, Genelle — SerenitySpaces Bahamas

### Step 1: Harvest leads (free, Google Maps + SunBiz + website crawling)
```bash
# Small test (recommended first)
/Users/mac/Ivybound/.venv/bin/python /Users/mac/Ivybound/harvest.py \
  --niche "executives" --cities "Miami FL,Fort Lauderdale FL,Tampa FL" --max-per-city 25

# Full Florida sweep
/Users/mac/Ivybound/.venv/bin/python /Users/mac/Ivybound/harvest.py \
  --niche "executives" --states "FL" --max-per-city 100

# Florida + Southeast (GA, AL, SC, NC for shoulder market)
/Users/mac/Ivybound/.venv/bin/python /Users/mac/Ivybound/harvest.py \
  --niche "executives" --states "FL,GA,AL,SC,NC" --max-per-city 75
```

### Step 2: Sync to Sheet
```bash
# After harvest completes
/Users/mac/Ivybound/.venv/bin/python /Users/mac/Ivybound/harvest.py --list-runs
/Users/mac/Ivybound/.venv/bin/python /Users/mac/Ivybound/harvest.py --sync-sheets <run_id>
```

**IMPORTANT:** Service account Drive quota is full. Before syncing:
1. Manually create a new Google Sheet titled `Bahamas Retreat - Campaign Leads`
2. Share it with the service account email (check `service_account_base64.txt` for the `client_email`)
3. Then run `--sync-sheets`

### Step 3: Launch send
```bash
nohup /Users/mac/Ivybound/.venv/bin/python /Users/mac/Ivybound/mailreef_automation/main.py \
  --profile BAHAMAS_RETREAT >> /Users/mac/Ivybound/logs/bahamas_retreat.log 2>&1 &
```

### Volume Ramp (same as Ivybound but on competitionhand)
| Week | Per-inbox/day | Daily total |
|---|---|---|
| 1 | 5 | 400 |
| 2 | 10 | 800 |
| 3 | 15 | 1,200 |
| 4+ | 20 | 1,600 |

---

## Daily Monitoring (BOTH CAMPAIGNS)

Run each morning before doing anything else:
```bash
/Users/mac/Ivybound/.venv/bin/python /Users/mac/Ivybound/check_warming_status.py
```

Watch for:
- **Bounce rate >2%** on any inbox → pause the inbox immediately
- **Complaint rate >0.3%** → pause the inbox immediately
- **Reply sentiment "negative"** → already auto-suppressed by reply_watcher.py
- **Smartlead warmup `0/25` counters** → should climb daily; if all stuck at 0, contact Smartlead support

## Kill-Switch

If anything looks wrong:
```bash
# Stop sender
ps aux | grep "main.py --profile" | grep -v grep | awk '{print $2}' | xargs kill

# Pause warmup if Smartlead is the issue
ps aux | grep warmup_engage | grep -v grep | awk '{print $2}' | xargs kill
```

## Expected Outcomes

| Campaign | Lead pool | Reply rate target | Replies/month | Meetings/month |
|---|---|---|---|---|
| Ivybound Summer | 10,076 | 2-5% | 200-500 | 50-125 |
| Bahamas Retreat | TBD post-scrape (target 2,000) | 3-7% | 60-140 | 15-35 |

---

## Files Reference

| Purpose | File |
|---|---|
| Campaign profiles | `mailreef_automation/automation_config.py` |
| Sender identities | `automation_config.py` (SENDER_IDENTITIES, BAHAMAS_SENDER_IDENTITIES) |
| Ivybound summer templates | `templates/school_summer/` |
| Bahamas templates | `templates/bahamas/` |
| Bahamas scraper | `lead_engine/bahamas_scraper.py` |
| Universal harvester | `harvest.py` |
| Email generator | `generators/email_generator.py` |
| Scheduler | `mailreef_automation/scheduler.py` |
| Reply watcher | `reply_watcher.py` (auto-suppress negative replies) |
| Warmup engagement | `warmup_engage.py` (replies to Mailreef warming pool) |
| Status checker | `check_warming_status.py` |
| Smartlead sync | `smartlead_sync.py` |
