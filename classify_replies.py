import os
import sys
import logging
import time
from typing import List, Dict, Any
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.getcwd())

from sheets_integration import GoogleSheetsClient
from reply_watcher import ReplyWatcher
import mailreef_automation.automation_config as automation_config

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("REPLY_CLASSIFIER")

def classify_replies_pass(profile_name="IVYBOUND"):
    logger.info(f"🚀 STARTING AI CLASSIFICATION PASS FOR {profile_name}")
    
    # 1. Initialize Clients
    watcher = ReplyWatcher(profile_name=profile_name)
    sheets = watcher.sheets_client
    
    # User's Profile Config
    profile_config = automation_config.CAMPAIGN_PROFILES[profile_name]
    worksheet_name = profile_config.get("replies_worksheet_name", "March")
    
    # 2. Fetch all rows from the worksheet
    try:
        worksheet = sheets.replies_sheet.worksheet(worksheet_name)
        records = worksheet.get_all_records()
        logger.info(f"Found {len(records)} replies to classify.")
    except Exception as e:
        logger.error(f"Could not load worksheet '{worksheet_name}': {e}")
        return

    # 3. Classify each row
    row_colors = []
    updates = [] # List of (row, col, value) for Sentiment column (approx Col 8 / H)
    
    # Color Constants
    GREEN = {'red': 0.85, 'green': 0.95, 'blue': 0.85}
    RED = {'red': 0.98, 'green': 0.85, 'blue': 0.85}
    
    for i, record in enumerate(records):
        row_num = i + 2 # 1-based, plus header
        body = record.get('Entire Thread', '') or record.get('Subject', '')
        
        if not body:
            continue
            
        logger.info(f"Classifying row {row_num}...")
        
        prompt = f"""Analyze the following email reply from a school administrator. 
Determine if it is "ACTIONABLE" or "UNACTIONABLE" based on these STRICT criteria:

ACTIONABLE: 
- You have reached the RIGHT PERSON (the administrator themselves or they are the decision maker).
- They are SOMEWHAT INTERESTED in having a conversation or meeting.
- Examples: "Let's talk", "Call me next week", "Sounds interesting", "I'm the person you need to speak with, tell me more".

UNACTIONABLE:
- Wrong person ("I'm not the one who handles this").
- Not interested / No response expected.
- Out of office / Auto-reply.
- Aggressive rejections.
- Forwarding to a generic info@ or another person without expressing their own interest first.

EMAIL CONTENT:
'''
{body}
'''

Return ONLY one word: ACTIONABLE or UNACTIONABLE."""

        try:
            response = watcher.generator.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10
            )
            classification = response.choices[0].message.content.strip().upper()
            logger.info(f"Result: {classification}")
            
            # Map to color
            color = GREEN if "ACTIONABLE" in classification and "UN" not in classification else RED
            row_colors.append({'row': row_num, 'color': color})
            
            # Also update the 'Sentiment' column in the sheet for metadata sync
            # Column H is Sentiment (8th column)
            updates.append({'range': f'H{row_num}', 'values': [[classification.lower()]]})
            
        except Exception as e:
            logger.error(f"Failed to classify row {row_num}: {e}")
            continue
            
        # Rate limiting prevent hitting GPT too hard too fast
        time.sleep(0.1)

    # 4. Apply Batch Updates
    if updates:
        # worksheet.batch_update is for values
        worksheet.batch_update(updates)
        logger.info(f"Updated classification labels for {len(updates)} rows.")
        
    if row_colors:
        # sheets.color_rows is our new custom method
        sheets.color_rows(worksheet_name, row_colors)
        logger.info(f"Applied visual color coding to {len(row_colors)} rows.")

    # 5. Sort the sheet
    sheets.sort_replies(worksheet_name)
    logger.info("🎉 CLASSIFICATION AND SORTING PASS COMPLETED.")

if __name__ == "__main__":
    classify_replies_pass()
