import os
import sys
import re
import time
import requests
import gspread
from gspread.exceptions import APIError
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.getcwd())

from sheets_integration import GoogleSheetsClient
from mailreef_automation.logger_util import get_logger
from openai import OpenAI

# Initialize Logger
logger = get_logger("REPLY_ENRICHER")
load_dotenv()

class ReplyEnricher:
    def __init__(self):
        self.api_key = os.getenv('MAILREEF_API_KEY')
        self.base_url = 'https://api.mailreef.com'
        self.ai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.sheets_client = GoogleSheetsClient(input_sheet_name='Ivy Bound - Campaign Leads')
        self.sheets_client.setup_sheets()
        self.golden_emails = [
            'claire@emeraldcoastacademics.com', 'jpickton@flprep.com', 'rgrandy@academyprep.org',
            'a.diaz@mytvca.org', 'empowerobc@gmail.com', 'standrewsbaystemacademy@gmail.com',
            'hatth82@gmail.com', 'jovanna@alphaperformance.net', 'cshey@riverstoneschool.org'
        ]
        
    def fetch_mailreef_replies(self, max_pages=40) -> Dict[str, List[Dict]]:
        """Fetch all historical inbound emails."""
        logger.info(f"📡 PERFORMING DEEP FETCH: Retrieving up to {max_pages*100} emails from Mailreef...")
        inbound_map = {}
        
        for page in range(1, max_pages + 1):
            try:
                logger.info(f"  ...Fetching page {page}/{max_pages}")
                response = requests.get(
                    f"{self.base_url}/mail/inbound",
                    auth=(self.api_key, ''),
                    params={'page': page, 'display': 100},
                    timeout=30
                )
                if response.status_code != 200:
                    logger.error(f"Failed to fetch page {page}: {response.text}")
                    break
                
                data = response.json()
                messages = data.get('data', [])
                if not messages:
                    break
                
                for msg in messages:
                    headers = msg.get('headers', {})
                    from_raw = headers.get('From', '')
                    # Extract email from "Name <email@domain.com>"
                    import re
                    match = re.search(r'<([^>]+)>', from_raw)
                    email = match.group(1).lower().strip() if match else from_raw.lower().strip()
                    
                    # Store by email and a unique identifier (ID)
                    if email not in inbound_map:
                        inbound_map[email] = []
                    
                    inbound_map[email].append(msg)
                
                if len(messages) < 100:
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching inbound: {e}")
                break
        
        return inbound_map

    def analyze_actionability(self, body: str) -> str:
        """Use AI to determine if a reply is actionable."""
        if not body.strip():
            return "Red (Empty)"
            
        try:
            prompt = f"""
            Analyze the following email response from a school administrator.
            Is this an ACTIONABLE lead (wants to meet, asking questions, positive) or NOT ACTIONABLE (auto-reply, rejection, unsubscribe, angry, or a listserv notification)?

            TEXT:
            \"\"\"{body[:2000]}\"\"\"

            Respond with ONLY one of these labels:
            - Green (Actionable)
            - Red (Not Actionable)
            
            Briefly explain why in one sentence if it is Red.
            Format: LABEL | REASON
            """
            response = self.ai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error: {str(e)}"

    def enrich_replies_sheet(self):
        logger.info("🚀 Starting Reply Enrichment and Cleanup...")
        
        # 1. Fetch Inbound Map
        inbound_map = self.fetch_mailreef_replies(max_pages=40)
        
        # 2. Load Spreadsheet
        worksheet = self.sheets_client.replies_sheet.sheet1
        all_records = worksheet.get_all_records()
        headers = worksheet.row_values(1)
        
        if 'Actionability' not in headers:
            worksheet.insert_cols([['Actionability']], len(headers) + 1)
            headers.append('Actionability')
            logger.info("Added 'Actionability' column to sheet.")

        updated_records = []
        rows_to_update = 0
        
        # 3. Separate Golden vs Regular for deduplication
        golden_leads = []
        regular_leads = {}
        
        for r in all_records:
            email = str(r.get('From Email', '')).lower().strip()
            notes = str(r.get('Notes', '')).upper()
            
            if email in self.golden_emails or 'GOLDEN' in notes:
                # Always preserve golden exactly as is (or with thread if missing)
                golden_leads.append(r)
            else:
                if email not in regular_leads:
                    regular_leads[email] = r
                else:
                    if len(str(r.get('Entire Thread', ''))) > len(str(regular_leads[email].get('Entire Thread', ''))):
                        regular_leads[email] = r
        
        final_list = list(regular_leads.values())
        logger.info(f"Deduplicated: Golden={len(golden_leads)}, Regular={len(final_list)}")

        # Audit regular leads
        for i, record in enumerate(final_list):
            email = str(record.get('From Email', '')).lower().strip()
            
            # If missing info, try to match
            if email in inbound_map:
                msgs = inbound_map[email]
                match = msgs[0] 
                
                # Update record
                record['Thread ID'] = match.get('id')
                record['Subject'] = match.get('headers', {}).get('Subject')
                record['Entire Thread'] = match.get('body_text') or match.get('body_html') or ""
                record['Original Sender'] = match.get('mailbox_id')
                
                # AI Analysis
                analysis = self.analyze_actionability(record['Entire Thread'])
                record['Actionability'] = analysis
                
                if 'Red' in analysis:
                    record['Sentiment'] = 'negative'
                elif 'Green' in analysis:
                    record['Sentiment'] = 'positive'
                
                rows_to_update += 1
                logger.info(f"[{i+1}/{len(final_list)}] ✅ MATCHED {email} -> {analysis}")
            else:
                record['Actionability'] = record.get('Actionability') or "Red (No Thread Record Matches Ivy Bound)"
                record['Sentiment'] = 'invalid'
                logger.info(f"[{i+1}/{len(final_list)}] ❌ NO MATCH for {email}")
                
            updated_records.append(record)

            # Progressive Update every 30 rows (optimized for quota)
            if (i + 1) % 30 == 0:
                self._flush_to_sheet(worksheet, headers, updated_records)
                time.sleep(10) # Safety gap
                time.sleep(5) # Give the API a breather

        # 4. Write back combining Golden (Top) + Regular
        total_final = golden_leads + updated_records
        self._flush_to_sheet(worksheet, headers, total_final)
        logger.info(f"🎉 Enrichment COMPLETE. Total Leads: {len(total_final)}")

    def _flush_to_sheet(self, worksheet, headers, records):
        """Helper to write current state to sheet with retries."""
        import time
        final_rows = []
        for record in records:
            row = []
            for h in headers:
                row.append(str(record.get(h, '')))
            final_rows.append(row)
        
        if final_rows:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Clear target area (don't clear whole sheet or it flickers)
                    cell_range = f'A2:{chr(64 + len(headers))}{len(final_rows) + 1}'
                    worksheet.update(cell_range, final_rows)
                    logger.info(f"💾 Flushed {len(final_rows)} rows to sheet...")
                    break
                except Exception as e:
                    if "429" in str(e) and attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 30
                        logger.warning(f"⚠️ Quota hit. Waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    logger.error(f"Failed to flush to sheet: {e}")
                    raise e

if __name__ == "__main__":
    enricher = ReplyEnricher()
    enricher.enrich_replies_sheet()
