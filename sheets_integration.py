#!/usr/bin/env python3
"""
Google Sheets Integration for Ivy Bound Email Campaign

Handles:
1. Reading leads from input sheet
2. Writing replies to tracking sheet
3. Updating lead status after sending

Usage:
    python sheets_integration.py --setup  # First-time OAuth setup
    python sheets_integration.py --test   # Test connection
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any

import time
from functools import wraps
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from gspread.exceptions import APIError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# OAuth scopes needed
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.readonly'
]

# File paths
CREDENTIALS_FILE = Path(__file__).parent / 'credentials' / 'google_oauth.json'
TOKEN_FILE = Path(__file__).parent / 'credentials' / 'token.json'

# Sheet names
INPUT_SHEET_NAME = "Ivy Bound - Campaign Leads"
REPLIES_SHEET_NAME = "Ivy Bound - Reply Tracking"


class GoogleSheetsClient:
    """Handles all Google Sheets operations for the campaign."""
    
    def __init__(self):
        self.client: Optional[gspread.Client] = None
        self.input_sheet: Optional[gspread.Spreadsheet] = None
        self.replies_sheet: Optional[gspread.Spreadsheet] = None
        
        # Caching
        self._cache = {} # email -> record
        self._all_records_cache = None
        self._last_all_records_fetch = datetime.min
        self.CACHE_TTL = timedelta(minutes=5)
        
        self._authenticate()

    def retry_on_quota(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            max_retries = 3
            for i in range(max_retries):
                try:
                    return f(*args, **kwargs)
                except APIError as e:
                    if "[429]" in str(e) and i < max_retries - 1:
                        wait = (i + 1) * 30 
                        logger.warning(f"⚠️ Google Sheets Quota hit. Waiting {wait}s before retry {i+1}/{max_retries}...")
                        time.sleep(wait)
                        continue
                    raise
            return f(*args, **kwargs)
        return wrapper

    @retry_on_quota
    def _fetch_all_records(self):
        """Internal helper to fetch all records with caching."""
        now = datetime.now()
        if self._all_records_cache is None or (now - self._last_all_records_fetch) > self.CACHE_TTL:
            logger.info("📡 Fetching fresh records from Google Sheets...")
            worksheet = self.input_sheet.sheet1
            self._all_records_cache = worksheet.get_all_records()
            self._last_all_records_fetch = now
            # Warm up individual cache with row numbers
            # index i in get_all_records corresponds to row i + 2 (1-based headers)
            for i, record in enumerate(self._all_records_cache):
                if record.get('email'):
                    record['_row'] = i + 2
                    self._cache[record['email']] = record
        return self._all_records_cache
    
    def _authenticate(self):
        """Authenticate with Google using OAuth credentials or a service account/token from env."""
        creds = None
        
        # 1. Try to load from environment variable (Best for Railway/Cloud)
        env_creds = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
        if env_creds:
            try:
                creds_dict = json.loads(env_creds)
                # Check if it's an authorized user token or a service account
                if "refresh_token" in creds_dict:
                    creds = Credentials.from_authorized_user_info(creds_dict, SCOPES)
                    logger.info("✓ Authenticated via GOOGLE_SHEETS_CREDENTIALS (User Token)")
                else:
                    # Fallback to service account if that's what's provided
                    from google.oauth2 import service_account
                    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
                    logger.info("✓ Authenticated via GOOGLE_SHEETS_CREDENTIALS (Service Account)")
            except Exception as e:
                logger.warning(f"Failed to load credentials from environment: {e}")

        # 2. Fallback to local token file (Best for local development)
        if not creds and TOKEN_FILE.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
                logger.info("✓ Authenticated via local token file")
            except Exception as e:
                logger.warning(f"Could not load token: {e}")
        
        # 3. If no valid credentials, run local OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = self._run_oauth_flow()
            else:
                creds = self._run_oauth_flow()
            
            # Save credentials locally for future use
            if creds and not env_creds:
                TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(TOKEN_FILE, 'w') as f:
                    f.write(creds.to_json())
        
        if creds:
            self.client = gspread.authorize(creds)
            logger.info("✓ Final Authentication Successful")
        else:
            raise Exception("Failed to authenticate with Google")
    
    def _run_oauth_flow(self) -> Optional[Credentials]:
        """Run the OAuth flow to get new credentials."""
        if not CREDENTIALS_FILE.exists():
            logger.error(f"OAuth credentials file not found at {CREDENTIALS_FILE}")
            logger.info("Please download OAuth credentials from Google Cloud Console")
            logger.info("1. Go to https://console.cloud.google.com/apis/credentials")
            logger.info("2. Create OAuth 2.0 Client ID (Desktop application)")
            logger.info("3. Download JSON and save to: credentials/google_oauth.json")
            return None
        
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
        creds = flow.run_local_server(port=8080)
        return creds
    
    def setup_sheets(self) -> Dict[str, str]:
        """Create the input and replies sheets if they don't exist."""
        results = {}
        
        # Create or get input sheet
        try:
            self.input_sheet = self.client.open(INPUT_SHEET_NAME)
            logger.info(f"✓ Found existing input sheet: {INPUT_SHEET_NAME}")
        except gspread.SpreadsheetNotFound:
            self.input_sheet = self.client.create(INPUT_SHEET_NAME)
            self._setup_input_sheet_headers()
            logger.info(f"✓ Created input sheet: {INPUT_SHEET_NAME}")
        
        results['input_sheet_url'] = self.input_sheet.url
        
        # Create or get replies sheet
        try:
            self.replies_sheet = self.client.open(REPLIES_SHEET_NAME)
            logger.info(f"✓ Found existing replies sheet: {REPLIES_SHEET_NAME}")
        except gspread.SpreadsheetNotFound:
            self.replies_sheet = self.client.create(REPLIES_SHEET_NAME)
            self._setup_replies_sheet_headers()
            logger.info(f"✓ Created replies sheet: {REPLIES_SHEET_NAME}")
        
        results['replies_sheet_url'] = self.replies_sheet.url
        
        return results
    
    def _setup_input_sheet_headers(self):
        """Set up headers for the input leads sheet."""
        worksheet = self.input_sheet.sheet1
        worksheet.update_title("Leads")
        
        headers = [
            "email",
            "first_name",
            "last_name",
            "role",
            "school_name",
            "domain",
            "state",
            "city",
            "phone",
            "status",           # pending, email_1_sent, email_2_sent, replied, bounced
            "email_1_sent_at",
            "email_2_sent_at",
            "sender_email",
            "notes"
        ]
        
        worksheet.update('A1:N1', [headers])
        worksheet.format('A1:N1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.2, 'green': 0.4, 'blue': 0.6}
        })
        
        logger.info("✓ Set up input sheet headers")
    
    def _setup_replies_sheet_headers(self):
        """Set up headers for the replies tracking sheet."""
        worksheet = self.replies_sheet.sheet1
        worksheet.update_title("Replies")
        
        headers = [
            "received_at",
            "from_email",
            "from_name",
            "school_name",
            "role",
            "subject",
            "snippet",          # First 200 chars of reply
            "sentiment",        # positive, neutral, negative, meeting_request
            "original_sender",  # Which inbox sent the original
            "original_subject",
            "thread_id",
            "action_taken",     # replied, forwarded, scheduled_meeting
            "notes"
        ]
        
        worksheet.update('A1:M1', [headers])
        worksheet.format('A1:M1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.4}
        })
        
        logger.info("✓ Set up replies sheet headers")
    
    def get_pending_leads(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get leads that haven't been contacted yet."""
        all_records = self._fetch_all_records()
        
        pending = [
            record for record in all_records 
            if record.get('status', '').lower() in ['', 'pending']
        ]
        
        logger.info(f"Found {len(pending)} pending leads (returning up to {limit})")
        return pending[:limit]
    
    def get_leads_for_followup(self, days_since_email_1: int = 3, 
                               sender_email: Optional[str] = None,
                               limit: int = 100) -> List[Dict[str, Any]]:
        """Get leads that received Email 1 and are due for Email 2."""
        all_records = self._fetch_all_records()
        
        followup_leads = []
        now = datetime.now()
        
        for record in all_records:
            # Must match sender email if specified
            if sender_email and record.get('sender_email') != sender_email:
                continue
                
            if record.get('status') == 'email_1_sent':
                sent_at_str = record.get('email_1_sent_at', '')
                if sent_at_str:
                    try:
                        sent_at = datetime.fromisoformat(sent_at_str)
                        days_elapsed = (now - sent_at).days
                        if days_elapsed >= days_since_email_1:
                            followup_leads.append(record)
                    except ValueError:
                        pass
            
            if len(followup_leads) >= limit:
                break
        
        logger.info(f"Found {len(followup_leads)} leads due for follow-up (Sender: {sender_email or 'Any'})")
        return followup_leads
    
    @retry_on_quota
    def update_lead_status(self, email: str, status: str, 
                           sent_at: Optional[datetime] = None,
                           sender_email: Optional[str] = None):
        """Update a lead's status after sending an email."""
        worksheet = self.input_sheet.sheet1
        
        # Find the row with this email
        try:
            # Check cache for row if possible
            cached_record = self._cache.get(email)
            if cached_record and cached_record.get('_row'):
                row = cached_record['_row']
            else:
                # Fallback to search if not in cache (should be rare)
                cell = worksheet.find(email)
                row = cell.row
            
            # Get column indices (Use a small cache for headers too)
            if not hasattr(self, '_headers_cache') or not self._headers_cache:
                self._headers_cache = worksheet.row_values(1)
            headers = self._headers_cache
            
            # Prepare batch updates
            cell_list = []
            
            status_col = headers.index('status') + 1
            cell_list.append(gspread.Cell(row, status_col, status))
            
            if sent_at:
                if status == 'email_1_sent':
                    col = headers.index('email_1_sent_at') + 1
                elif status == 'email_2_sent':
                    col = headers.index('email_2_sent_at') + 1
                else:
                    col = None
                
                if col:
                    cell_list.append(gspread.Cell(row, col, sent_at.isoformat()))
            
            if sender_email:
                sender_col = headers.index('sender_email') + 1
                cell_list.append(gspread.Cell(row, sender_col, sender_email))
            
            # Perform Batch Update
            worksheet.update_cells(cell_list)
            
            # Invalidate local cache for this email
            if email in self._cache:
                self._cache[email].update({
                    'status': status,
                    'sender_email': sender_email or self._cache[email].get('sender_email')
                })
            
            logger.info(f"Updated {email} status to {status} (Batch)")
            
        except gspread.CellNotFound:
            logger.warning(f"Lead not found: {email}")
    
    def log_reply(self, reply_data: Dict[str, Any]):
        """Log a reply to the replies sheet."""
        worksheet = self.replies_sheet.sheet1
        
        row = [
            reply_data.get('received_at', datetime.now().isoformat()),
            reply_data.get('from_email', ''),
            reply_data.get('from_name', ''),
            reply_data.get('school_name', ''),
            reply_data.get('role', ''),
            reply_data.get('subject', ''),
            reply_data.get('snippet', '')[:200],
            reply_data.get('sentiment', 'neutral'),
            reply_data.get('original_sender', ''),
            reply_data.get('original_subject', ''),
            reply_data.get('thread_id', ''),
            reply_data.get('action_taken', ''),
            reply_data.get('notes', '')
        ]
        
        worksheet.append_row(row)
        logger.info(f"Logged reply from {reply_data.get('from_email')}")
        
        # Also update the lead status in input sheet
        self.update_lead_status(reply_data.get('from_email', ''), 'replied')


def setup_oauth():
    """Interactive setup for OAuth credentials."""
    print("\n" + "="*60)
    print("GOOGLE SHEETS OAUTH SETUP")
    print("="*60 + "\n")
    
    credentials_dir = Path(__file__).parent / 'credentials'
    credentials_dir.mkdir(exist_ok=True)
    
    if not CREDENTIALS_FILE.exists():
        print("To connect to Google Sheets, you need OAuth credentials.\n")
        print("STEPS:")
        print("1. Go to: https://console.cloud.google.com/apis/credentials")
        print("2. Create a project (or select existing)")
        print("3. Enable 'Google Sheets API' and 'Google Drive API'")
        print("4. Create OAuth 2.0 Client ID (Desktop application)")
        print("5. Download the JSON file")
        print(f"6. Save it as: {CREDENTIALS_FILE}")
        print("\nOnce done, run this script again with --setup")
        return
    
    print("OAuth credentials found. Authenticating...")
    client = GoogleSheetsClient()
    
    print("\nCreating/connecting to sheets...")
    urls = client.setup_sheets()
    
    print("\n" + "="*60)
    print("✓ SETUP COMPLETE!")
    print("="*60)
    print(f"\nInput Sheet:  {urls['input_sheet_url']}")
    print(f"Replies Sheet: {urls['replies_sheet_url']}")
    print("\nYou can now add leads to the input sheet and the system will")
    print("automatically pull from it and track replies.")


def test_connection():
    """Test the Google Sheets connection."""
    print("Testing Google Sheets connection...")
    
    try:
        client = GoogleSheetsClient()
        urls = client.setup_sheets()
        
        # Test reading from input sheet
        leads = client.get_pending_leads(limit=5)
        print(f"✓ Connected to input sheet ({len(leads)} pending leads found)")
        
        # Test reading from replies sheet
        worksheet = client.replies_sheet.sheet1
        rows = worksheet.get_all_values()
        print(f"✓ Connected to replies sheet ({len(rows)-1} replies logged)")
        
        print("\n✓ All connections working!")
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Google Sheets Integration')
    parser.add_argument('--setup', action='store_true', help='Run first-time setup')
    parser.add_argument('--test', action='store_true', help='Test connection')
    
    args = parser.parse_args()
    
    if args.setup:
        setup_oauth()
    elif args.test:
        test_connection()
    else:
        parser.print_help()
