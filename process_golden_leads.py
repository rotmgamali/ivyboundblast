import os
import sys
import logging
import time
import json
from datetime import datetime
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.getcwd())

from sheets_integration import GoogleSheetsClient
from reply_watcher import ReplyWatcher
import mailreef_automation.automation_config as automation_config

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GOLDEN_LEADS")

def process_golden_leads(profile_name="IVYBOUND"):
    logger.info(f"🌟 STARTING GOLDEN LEAD ENRICHMENT FOR {profile_name}")
    
    # 1. Initialize Clients
    watcher = ReplyWatcher(profile_name=profile_name)
    sheets = watcher.sheets_client
    
    # User's Profile Config
    profile_config = automation_config.CAMPAIGN_PROFILES[profile_name]
    worksheet_name = profile_config.get("replies_worksheet_name", "March")
    
    # 2. Fetch all rows
    try:
        worksheet = sheets.replies_sheet.worksheet(worksheet_name)
        records = worksheet.get_all_records()
    except Exception as e:
        logger.error(f"Could not load worksheet '{worksheet_name}': {e}")
        return

    # Filter for actionable leads
    actionable_rows = []
    for i, record in enumerate(records):
        if str(record.get('Sentiment', '')).lower() == 'actionable':
            actionable_rows.append({'row_num': i + 2, 'record': record})
            
    logger.info(f"Processing {len(actionable_rows)} actionable leads...")

    # Color for GOLDEN
    GOLD = {'red': 1.0, 'green': 0.92, 'blue': 0.6}
    
    row_colors = []
    updates = [] # List of dicts for batch_update [[Sentiment, Notes]]

    for item in actionable_rows:
        row_num = item['row_num']
        record = item['record']
        body = record.get('Entire Thread', '') or record.get('Subject', '')
        
        logger.info(f"Analyzing Golden Lead at row {row_num}: {record.get('From Email')}")
        
        prompt = f"""Analyze this actionable email lead from a school administrator.
Identify the specific REASON it is high-value and the RECENT REPLY DATE.
Suggest a specific NEXT ACTION/PITCH for the follow-up email.

EMAIL CONTENT:
'''
{body}
'''

Return EXACTLY in this JSON format:
{{
  "reason": "short sentence on why it's actionable",
  "reply_date": "YYYY-MM-DD",
  "next_action": "what we should email them next"
}}"""

        try:
            response = watcher.generator.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={ "type": "json_object" }
            )
            analysis = json.loads(response.choices[0].message.content)
            
            reasoning = analysis.get("reason", "Highly interested decision maker.")
            date_str = analysis.get("reply_date", datetime.now().strftime("%Y-%m-%d"))
            next_step = analysis.get("next_action", "Propose a quick meeting to discuss specifics.")
            
            full_note = f"REASON: {reasoning} | ACTION: {next_step}"
            
            # Updates: 
            # Col H (8) is Sentiment
            # Col M (13) is Notes
            # Col A (1) is Received At (Updating it with processed date)
            
            updates.append({'range': f'H{row_num}', 'values': [['GOLDEN 🌟']]})
            updates.append({'range': f'M{row_num}', 'values': [[full_note]]})
            updates.append({'range': f'A{row_num}', 'values': [[date_str]]})
            
            row_colors.append({'row': row_num, 'color': GOLD})
            
        except Exception as e:
            logger.error(f"Failed to process row {row_num}: {e}")
            continue
            
        time.sleep(0.1)

    # Apply Updates
    if updates:
        worksheet.batch_update(updates)
        logger.info(f"Updated metadata for {len(updates)//3} golden leads.")
        
    if row_colors:
        sheets.color_rows(worksheet_name, row_colors)
        logger.info(f"Applied Golden highlights to {len(row_colors)} rows.")

    # Re-sort to put GOLDEN at top
    sheets.sort_replies(worksheet_name)
    logger.info("🎉 GOLDEN LEAD PROCESSING COMPLETE.")

if __name__ == "__main__":
    process_golden_leads()
