"""
Scheduler module for automated email sending
Uses APScheduler for cron-like functionality
"""

import random
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import sys
import os

# Add project root to path to ensure generators/scrapers can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generators.email_generator import EmailGenerator
from logger_util import get_logger

logger = get_logger("SCHEDULER")

class EmailScheduler:
    """Manages the scheduling logic for all email sends"""
    
    def __init__(self, mailreef_client, config):
        self.mailreef = mailreef_client
        # Remove SQLite ContactManager
        # self.contacts = contact_manager 
        self.config = config
        self.scheduler = BackgroundScheduler(timezone=pytz.timezone('US/Eastern'))
        self.generator = EmailGenerator()
        
        # Cloud-Native: Sheets Integration
        from sheets_integration import GoogleSheetsClient
        self.sheets = GoogleSheetsClient()
        self.sheets.setup_sheets()
        
        # Local Cache to prevent Sheets API Rate Limits
        self._lead_cache = []
        self._last_cache_update = datetime.min
        self.CACHE_DURATION = timedelta(minutes=15)
        
        self.is_running = False
        
    def calculate_daily_send_requirements(self, day_type):
        """Calculate how many emails each inbox should send today"""
        if day_type == "business":
            active_inboxes = self.config.INBOXES_PER_DAY_BUSINESS
            emails_per_inbox = self.config.EMAILS_PER_INBOX_DAY_BUSINESS
        else:
            active_inboxes = self.config.INBOXES_PER_DAY_WEEKEND
            emails_per_inbox = self.config.EMAILS_PER_INBOX_DAY_WEEKEND
            
        return {
            "total_emails": active_inboxes * emails_per_inbox,
            "active_inboxes": active_inboxes,
            "emails_per_inbox": emails_per_inbox
        }
    
    def generate_send_slots(self, day_type, inbox_count):
        """Generate time slots for sending emails with natural variance"""
        windows = (self.config.BUSINESS_DAY_WINDOWS 
                   if day_type == "business" 
                   else self.config.WEEKEND_DAY_WINDOWS)
        
        slots = []
        
        # Fetch real inboxes from API
        try:
            all_inboxes = self.mailreef.get_inboxes()
            # Sort by ID to ensure consistent rotation order
            all_inboxes.sort(key=lambda x: x['id'])
        except Exception as e:
            print(f"Failed to fetch inboxes: {e}")
            return []

        total_inboxes_available = len(all_inboxes)
        active_inboxes = []

        if day_type == "business":
            # Rotation logic: (day_of_year * 2) % total_inboxes
            # We want to PAUSE 2 inboxes.
            day_of_year = datetime.now(pytz.timezone('US/Eastern')).timetuple().tm_yday
            
            if total_inboxes_available > 0:
                start_pause_index = (day_of_year * 2) % total_inboxes_available
                paused_indices = {start_pause_index, (start_pause_index + 1) % total_inboxes_available}
                
                for i, inbox in enumerate(all_inboxes):
                    if i not in paused_indices:
                        active_inboxes.append(inbox)
                
                print(f"Business day rotation: Pausing inboxes at indices {paused_indices}")
            else:
                 print("No inboxes found to schedule.")
                
        else:
            # Weekend: All inboxes active
            active_inboxes = all_inboxes
            print("Weekend: All inboxes active")
        
        emails_assigned_per_inbox = {}
        for inbox in active_inboxes:
            emails_assigned_per_inbox[inbox['id']] = 0
            
        for window in windows:
            emails_per_inbox = window["emails_per_inbox"]
            window_start = window["start"]
            window_end = window["end"]
            
            for inbox_id in emails_assigned_per_inbox.keys():
                # We need to send 'emails_per_inbox' number of emails in this window
                for _ in range(emails_per_inbox):
                    # Add random jitter
                    random_minute = random.randint(0, 59)
                    
                    # If we are scheduling for the current hour, ensure send_time is in the future
                    now_est = datetime.now(pytz.timezone('US/Eastern'))
                    
                    if window_start == now_est.hour:
                        # Schedule in the next 2-10 minutes for "immediate" demo effect
                        jitter_minutes = now_est.minute + random.randint(2, 10)
                        if jitter_minutes >= 60: # Wrap around if at end of hour
                            jitter_minutes = 59 
                    else:
                        # Standard jitter: send 20-40 minutes into window base
                        jitter_minutes = random.randint(20, 40)
                    
                    send_time = now_est.replace(
                        hour=window_start,
                        minute=jitter_minutes,
                        second=0,
                        microsecond=0
                    )
                    
                    # Add 1-5 minute random offset to avoid all sending at exact same second
                    offset_seconds = random.randint(60, 300)
                    send_time = send_time + timedelta(seconds=offset_seconds)
                    
                    # logger.debug(f"Generated slot for inbox {inbox_id} at {send_time} (Window: {window_start}:00)")
                    
                    slots.append({
                        "inbox_id": inbox_id,
                        "scheduled_time": send_time,
                        "window": f"{window_start}:00-{window_end}:00"
                    })
                    
                    emails_assigned_per_inbox[inbox_id] += 1
        
        # Sort slots by time to be nice
        slots.sort(key=lambda x: x['scheduled_time'])
        return slots
    
    def _refresh_cache_if_needed(self):
        """Refresh local lead cache if expired or empty"""
        now = datetime.now()
        if not self._lead_cache or (now - self._last_cache_update) > self.CACHE_DURATION:
            logger.info("🔄 Refreshing lead cache from Sheets...")
            try:
                # Fetch more than we strictly need to act as a buffer
                new_batch = self.sheets.get_pending_leads(limit=50) 
                
                # Check for duplicates to avoid re-adding if cache isn't fully empty
                # Actually, simpler to just replace cache and assume FIFO
                if new_batch:
                    self._lead_cache = new_batch
                    self._last_cache_update = now
                    logger.info(f"✅ Cached {len(new_batch)} fresh leads.")
                else:
                    logger.warning("⚠️ No pending leads found in Sheet!")
            except Exception as e:
                logger.error(f"❌ Failed to refresh cache: {e}")

    def select_prospects_for_send(self, inbox_id, count, sequence_stage):
        """Select prospects for a specific send slot (Sheets-First)"""
        
        # Stage 2: Lead Consistency
        # Must find a lead that was sent Email 1 by THIS inbox
        if sequence_stage == 2:
            try:
                # Optimized: If inbox_id looks like an email, use it directly (saves API call & error prone lookup)
                if '@' in str(inbox_id):
                    inbox_email = str(inbox_id)
                else:
                    # Slow but safe: fetch inbox list to find email. 
                    inbox_email = None
                    inboxes = self.mailreef.get_inboxes()
                    for ibx in inboxes:
                        if str(ibx.get('id')) == str(inbox_id):
                            # API might return 'email' or 'address'
                            inbox_email = ibx.get('email') or ibx.get('address')
                            # Fallback: construct from username@domain if available
                            if not inbox_email and ibx.get('username') and ibx.get('domain'):
                                inbox_email = f"{ibx['username']}@{ibx['domain']}"
                            break
                
                if inbox_email:
                    return self.sheets.get_leads_for_followup(sender_email=inbox_email, limit=count)
                else:
                    logger.warning(f"Could not resolve email for inbox ID {inbox_id} (Data: {inboxes[0] if 'inboxes' in locals() and inboxes else 'Empty'})")
                    return []
            except Exception as e:
                logger.error(f"Error fetching follow-ups for inbox {inbox_id}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return []

        # Stage 1: New Leads (Use Cache)
        if sequence_stage == 1:
            self._refresh_cache_if_needed()
            
            # Pop from cache
            selected = []
            for _ in range(count):
                if self._lead_cache:
                    selected.append(self._lead_cache.pop(0))
                else:
                    break
            
            return selected
            
        return []
    
    def execute_send(self, inbox_id, prospects, sequence_number=1):
        """Execute the actual send via Mailreef API"""
        results = []
        for prospect in prospects:
            try:
                # Use High-Fidelity Generator
                logger.info(f"🚀 [SEND START] Generating personalized email for {prospect.get('email')}...")
                
                # Note: Sheets Row provides 'school_name', 'domain', 'first_name', 'role', etc.
                result = self.generator.generate_email(
                    campaign_type="school",
                    sequence_number=sequence_number,
                    lead_data=dict(prospect),
                    enrichment_data={} # Scrapes live
                )
                
                subject = result['subject']
                body_html = result['body'].replace('\n', '<br>')
                
                response = self.mailreef.send_email(
                    inbox_id=inbox_id,
                    to_email=prospect["email"],
                    subject=subject,
                    body=f"<html><body>{body_html}</body></html>"
                )
                
                logger.info(f"✅ [SEND SUCCESS] Email sent to {prospect['email']} via inbox {inbox_id}. MsgID: {response.get('message_id')}")
                
                # Sheets-First: Update Status Immediately
                # We need the sender email to record who sent it
                # We can perform a lookup or pass it if available.
                # Optimization: get email from result/response or lookup?
                # Mailreef API response might contain 'from'? Probably not.
                # Let's resolve specific sender email again or assume rotation logic valid.
                
                # Fetch sender email just for logging (could optimize this out)
                sender_email = "unknown"
                try:
                    inboxes = self.mailreef.get_inboxes()
                    for ibx in inboxes:
                        if str(ibx['id']) == str(inbox_id):
                            sender_email = ibx['email']
                            break
                except: pass

                status = f"email_{sequence_number}_sent"
                self.sheets.update_lead_status(
                    email=prospect["email"],
                    status=status,
                    sent_at=datetime.now(),
                    sender_email=sender_email
                )
                
                results.append({
                    "email": prospect["email"],
                    "status": "sent",
                    "mailreef_message_id": response.get("message_id")
                })
            except Exception as e:
                # Log failure
                logger.error(f"❌ [SEND FAILURE] Failed to send to {prospect.get('email')}: {e}")
                # Optional: Mark as failed in sheet?
                # self.sheets.update_lead_status(prospect["email"], "failed")
                
        return results
    
    def start(self):
        """Start the scheduler"""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            print("Scheduler started")
            self._schedule_daily_runs()
            
            # Run immediate prep for first launch
            print("Triggering immediate queue preparation...")
            self._prepare_daily_queue()
    
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        self.is_running = False
        print("Scheduler stopped")
    
    def _schedule_daily_runs(self):
        """Schedule the daily send preparation"""
        # Run at 5:00 AM EST to prepare the day's queue
        self.scheduler.add_job(
            self._prepare_daily_queue,
            CronTrigger(hour=5, minute=0, day_of_week='0-6', timezone='US/Eastern'),
            id='daily_prepare',
            replace_existing=True
        )
        print("Daily preparation job scheduled for 5:00 AM EST")
    
    def _prepare_daily_queue(self):
        """Prepare and queue all sends for the day"""
        logger.info("📅 Starting daily queue preparation...")
        now = datetime.now(pytz.timezone('US/Eastern'))
        day_of_week = now.weekday()
        
        if day_of_week in [5, 6]:  # Weekend
            day_type = "weekend"
            inbox_count = self.config.INBOXES_PER_DAY_WEEKEND
        else:  # Business day
            day_type = "business"
            inbox_count = self.config.INBOXES_PER_DAY_BUSINESS
        
        # Generate slots
        slots = self.generate_send_slots(day_type, inbox_count)
        logger.info(f"🎯 Generated {len(slots)} send slots for today ({day_type}).")
        
        # Schedule each slot
        for slot in slots:
            self.scheduler.add_job(
                self._execute_slot,
                'date',
                run_date=slot["scheduled_time"],
                args=[slot["inbox_id"], slot["scheduled_time"]],
                id=f'slot_{slot["inbox_id"]}_{slot["scheduled_time"].strftime("%Y%m%d%H%M%S")}_{random.randint(1000,9999)}',
                misfire_grace_time=3600 # Allow catchup if system was briefly down
            )
    
    def _execute_slot(self, inbox_id, scheduled_time):
        """Execute a single send slot with sequence prioritization"""
        # Prioritize Follow-ups (Stage 2) first
        prospects = self.select_prospects_for_send(inbox_id, count=1, sequence_stage=2)
        stage = 2
        
        if not prospects:
            # If no follow-ups due, pick a new Stage 1 lead
            prospects = self.select_prospects_for_send(inbox_id, count=1, sequence_stage=1)
            stage = 1
        
        if prospects:
            logger.info(f"⏰ [SLOT FIRE] Executing Stage {stage} send for {prospects[0].get('email')} from inbox {inbox_id}")
            self.execute_send(inbox_id, prospects, sequence_number=stage)
        else:
             # logger.debug(f"🔇 [SLOT FIRE] No prospects (Stage 1 or 2) found for inbox {inbox_id} at {scheduled_time}")
             pass
