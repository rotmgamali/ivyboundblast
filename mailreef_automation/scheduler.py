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
    
    def __init__(self, mailreef_client, contact_manager, config):
        self.mailreef = mailreef_client
        self.contacts = contact_manager
        self.config = config
        self.scheduler = BackgroundScheduler(timezone=pytz.timezone('US/Eastern'))
        self.generator = EmailGenerator()
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
            # So we skip 2 inboxes starting at the calculated index.
            day_of_year = datetime.now(pytz.timezone('US/Eastern')).timetuple().tm_yday
            
            if total_inboxes_available > 0:
                start_pause_index = (day_of_year * 2) % total_inboxes_available
                
                # Determine indices to pause (handling wrap-around)
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

        # Limit to the requested count if for some reason we have more than needed 
        # (though the logic above effectively selects the active set)
        # The prompt "inbox_count" argument is actually "active_inboxes" count target from config.
        # We should rely on our rotation logic which naturally results in Total - 2 for business days.
        
        emails_assigned_per_inbox = {}
        for inbox in active_inboxes:
            emails_assigned_per_inbox[inbox['id']] = 0
            
        for window in windows:
            emails_per_inbox = window["emails_per_inbox"]
            window_start = window["start"]
            window_end = window["end"]
            
            for inbox_id in emails_assigned_per_inbox.keys():
                current_count = emails_assigned_per_inbox[inbox_id]
                
                # We need to send 'emails_per_inbox' number of emails in this window
                # The loop here was logic heavy in the prompt, simplifying to standard slot generation
                
                for _ in range(emails_per_inbox):
                    # Add random jitter: send 20-40 minutes into window base
                    # But we also need to distribute within the hour.
                    # Simple approach: Pick a random minute in the hour
                    
                    random_minute = random.randint(0, 59)
                    
                    # Ensure we are within the window start/end hours
                    # If window is 1 hour length, just use the start hour
                    
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
                    
                    # If send_time is in the past for today, we might want to schedule for tomorrow? 
                    # But the daily queue runs at 5 AM, so this should generally be future.
                    logger.debug(f"Generated slot for inbox {inbox_id} at {send_time} (Window: {window_start}:00)")
                    
                    slots.append({
                        "inbox_id": inbox_id,
                        "scheduled_time": send_time,
                        "window": f"{window_start}:00-{window_end}:00"
                    })
                    
                    emails_assigned_per_inbox[inbox_id] += 1
        
        return slots
    
    def select_prospects_for_send(self, inbox_id, count, sequence_stage):
        """Select prospects for a specific send slot"""
        return self.contacts.get_pending_for_inbox(
            inbox_id=inbox_id,
            count=count,
            sequence_stage=sequence_stage
        )
    
    def execute_send(self, inbox_id, prospects, sequence_number=1):
        """Execute the actual send via Mailreef API"""
        results = []
        for prospect in prospects:
            try:
                # Use High-Fidelity Generator
                logger.info(f"🚀 [SEND START] Generating personalized email for {prospect.get('email')}...")
                
                # Note: ContactManager Row provides 'school_name', 'domain', 'first_name', 'role', etc.
                # Enrichment data is handled inside generator via live scrape
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
                
                self.contacts.record_send(
                    contact_id=prospect["id"],
                    inbox_id=inbox_id,
                    campaign_id=1, # Default campaign
                    sequence_stage=sequence_number,
                    message_id=response.get("message_id")
                )
                
                results.append({
                    "prospect_id": prospect["id"],
                    "status": "sent",
                    "mailreef_message_id": response.get("message_id")
                })
            except Exception as e:
                # Log failure
                logger.error(f"❌ [SEND FAILURE] Failed to send to {prospect.get('email')}: {e}")
                self.contacts.record_send(
                    contact_id=prospect["id"],
                    inbox_id=inbox_id,
                    campaign_id=1, 
                    sequence_stage=1, 
                    message_id=None,
                    status="failed",
                    error=str(e)
                )

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
            # Note: In a real high-volume system, you might not schedule 2000 individual jobs.
            # You might schedule 'windows' that process a batch.
            # But for 95 inboxes * 2 emails/hour, it's manageable.
            
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
            logger.debug(f"🔇 [SLOT FIRE] No prospects (Stage 1 or 2) found for inbox {inbox_id} at {scheduled_time}")
