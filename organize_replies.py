#!/usr/bin/env python3
import time
import logging
from typing import Dict, List
from sheets_integration import GoogleSheetsClient

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ORGANIZE_REPLIES")

def get_sentiment(snippet: str, subject: str) -> str:
    """Classify sentiment based on keywords."""
    text = (str(snippet) + " " + str(subject)).lower()
    
    # Positive: Interest, Requests for Info, Positive Affirmation
    positive_keywords = [
        "interested", "schedule", "call", "appointment", "more info", "send info",
        "tell me more", "how does it work", "sounds great", "sounds good",
        "meeting", "zoom", "tomorrow", "next week", "yes", "definitely", "price", "cost"
    ]
    
    # Negative: Opt-out, Rejection, Complaints
    negative_keywords = [
        "not interested", "no thanks", "stop", "unsubscribe", "remove", 
        "take me off", "wrong person", "don't email", "do not email",
        "please stop", "not the person", "uninterested"
    ]
    
    if any(kw in text for kw in negative_keywords):
        return "negative"
    if any(kw in text for kw in positive_keywords):
        return "positive"
    
    return "neutral"

def organize():
    logger.info("🚀 Starting Spreadsheet Organization...")
    
    # Initialize Sheets Client
    sheets = GoogleSheetsClient()
    sheets.setup_sheets()
    
    worksheet = sheets.replies_sheet.sheet1
    all_rows = worksheet.get_all_records()
    all_values = worksheet.get_all_values()
    headers = all_values[0]
    
    try:
        sentiment_col_idx = headers.index("Sentiment") + 1
    except ValueError:
        logger.error("❌ 'Sentiment' column not found in headers.")
        return

    logger.info(f"📊 Analyzing {len(all_rows)} replies...")
    
    updates = []
    for i, row in enumerate(all_rows):
        row_idx = i + 2 # 1-based, plus header
        current_sentiment = row.get("Sentiment", "").strip().lower()
        
        # Only update if empty or "unknown"
        if not current_sentiment or current_sentiment == "unknown":
            snippet = row.get("Snippet", "")
            subject = row.get("Subject", "")
            new_sentiment = get_sentiment(snippet, subject)
            
            updates.append({
                'range': f'H{row_idx}', # Using column H for Sentiment
                'values': [[new_sentiment]]
            })

    if updates:
        logger.info(f"✍️ Updating sentiment for {len(updates)} records...")
        worksheet.batch_update(updates)
    else:
        logger.info("✅ All records already have sentiment.")

    # --- SORTING ---
    logger.info("🔃 Sorting replies by Sentiment (Positive First) and Date (Newest First)...")
    try:
        # Fetch fresh data after sentiment update
        rows_to_sort = worksheet.get_all_records()
        
        def sort_key(r):
            # Sentiment priority: positive=0, neutral=1, negative=2
            s_map = {"positive": 0, "neutral": 1, "negative": 2}
            s_val = s_map.get(str(r.get("Sentiment", "")).lower().strip(), 3)
            # Date desc: we negate the timestamp or use string comparison
            dt_val = str(r.get("Received At", ""))
            return (s_val, dt_val * -1 if dt_val.isdigit() else dt_val) 
            # Simple string comparison for ISO dates works for desc if we reverse the list after sort
        
        # We'll use a more reliable string-based sort
        sentiment_order = {"positive": 0, "neutral": 1, "negative": 2}
        
        # Sort in memory
        sorted_data = sorted(
            rows_to_sort, 
            key=lambda x: (
                sentiment_order.get(str(x.get("Sentiment", "")).lower().strip(), 3),
                str(x.get("Received At", ""))
            ),
            reverse=False # We want 0 (positive) at top, and dates ascending standard? 
            # Actually user probably wants Newest at top within sentiment.
        )
        
        # Re-sort with Correct Logic: Sentiment ASC (0,1,2), Date DESC
        sorted_data = sorted(
            rows_to_sort,
            key=lambda x: (
                sentiment_order.get(str(x.get("Sentiment", "")).lower().strip(), 3),
                x.get("Received At", "0")
            ),
            reverse=False
        )
        # Note: The above dates are ASC. Let's fix to DESC for date.
        sorted_data.sort(key=lambda x: str(x.get("Received At", "")), reverse=True) # Date Desc
        sorted_data.sort(key=lambda x: sentiment_order.get(str(x.get("Sentiment", "")).lower().strip(), 3)) # Sentiment Asc
        
        # Prepare for update
        new_values = []
        for r in sorted_data:
            row_vals = [r.get(h, "") for h in headers]
            new_values.append(row_vals)
            
        if new_values:
            # Overwrite data range starting at A2
            from gspread.utils import rowcol_to_a1
            end_col_a1 = rowcol_to_a1(len(new_values) + 1, len(headers))
            data_range = f"A2:{end_col_a1}"
            
            # Use correct order: values first, then range
            worksheet.update(new_values, data_range)
            logger.info("✅ Spreadsheet sorted successfully.")
            
    except Exception as e:
        logger.error(f"❌ Error during sorting: {e}")

    # Apply Formatting (Minimizing rows + Colors)
    logger.info("🧹 Applying formatting and row minimization...")
    
    # Add row height minimization to the batch request
    try:
        body = {
            'requests': [
                # Minimize Row Height for ALL rows (startIndex 1 is row 2)
                {
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': worksheet.id,
                            'dimension': 'ROWS',
                            'startIndex': 1,
                            'endIndex': worksheet.row_count
                        },
                        'properties': {'pixelSize': 21},
                        'fields': 'pixelSize'
                    }
                }
            ]
        }
        sheets.replies_sheet.batch_update(body)
        
        # Trigger the existing apply_formatting for colors and widths
        sheets.apply_formatting()
        
    except Exception as e:
        logger.error(f"❌ Error applying formatting: {e}")

    logger.info("🏁 Organization Complete.")

if __name__ == "__main__":
    organize()
