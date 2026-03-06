import os
import sys
import gspread
from gspread.utils import a1_range_to_grid_range

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from sheets_integration import GoogleSheetsClient

# --- CONFIGURATION ---
SHEET_NAME = "Ivy Bound - Reply Tracking"

WARMUP_KEYWORDS = [
    "cycling club", "travel plans", "staff wellness", "project milestone",
    "budget plan", "quarterly results", "customer engagement", "tech stack",
    "software training", "company picnic", "employee satisfaction", "sales report",
    "internal announcement", "performance review", "department meeting",
    "webinar invitation", "vacation policy", "networking event",
    "melnyresults", "brandingsavoir", "marketingsavoir", "sendemallcloud", 
    "gcodeai", "influumcn", "gpatry", "gtwcfq", "gvbqlx", "ufiiqxj", "ufkjde",
    "w-8ben", "tax documentation"
]

SENTIMENT_RULES = {
    "HOT": ["yes", "interested", "sure", "available", "call", "phone", "talk", "hear more", "set up", "schedule", "demo", "meeting", "zoom"],
    "WARM": ["maybe", "later", "future", "keep me", "send info", "send details", "forward", "reaching out", "review"],
    "COLD": ["no", "not interested", "unsubscribe", "stop", "pass", "remove", "don't", "do not"],
    "REMOVED": ["wrong person", "bounce", "error", "fail", "blocked", "vacation", "auto-reply", "out of office"]
}

def is_warmup(text: str) -> bool:
    text = text.lower()
    return any(k in text for k in WARMUP_KEYWORDS)

def classify_sentiment(text: str) -> str:
    text = text.lower()
    
    # Priority: REMOVED -> COLD -> HOT -> WARM -> NEUTRAL
    # We want to catch hard no's first? Or hard yes's?
    # Usually "Not interested" is specific.
    
    for k in SENTIMENT_RULES["REMOVED"]:
        if k in text: return "REMOVED"
        
    for k in SENTIMENT_RULES["COLD"]:
        if k in text: return "COLD"
        
    for k in SENTIMENT_RULES["HOT"]:
        if k in text: return "HOT"
        
    for k in SENTIMENT_RULES["WARM"]:
        if k in text: return "WARM"
        
    return "NEUTRAL"

def apply_color_coding(worksheet):
    print("🎨 Applying Color Coding Rules...")
    
    # Define colors (RGB 0-1)
    GREEN = {'red': 0.85, 'green': 0.93, 'blue': 0.83}    # HOT
    YELLOW = {'red': 1.0, 'green': 0.95, 'blue': 0.8}     # WARM
    GREY = {'red': 0.9, 'green': 0.9, 'blue': 0.9}        # COLD / NEUTRAL
    RED = {'red': 0.96, 'green': 0.85, 'blue': 0.85}      # REMOVED
    
    # Column H is Sentiment (Index 7)
    # Range is A2:M1000 (assuming header is row 1)
    
    start_index = 1 # Row 2
    
    requests = []
    
    # Helper for rule
    def create_rule(value, color, priority):
        return {
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [a1_range_to_grid_range('A2:M1000', sheet_id=worksheet.id)],
                    'booleanRule': {
                        'condition': {
                            'type': 'CUSTOM_FORMULA',
                            'values': [{'userEnteredValue': f'=$H2="{value}"'}]
                        },
                        'format': {'backgroundColor': color}
                    }
                },
                'index': priority
            }
        }

    # Add rules (Target index 0 means "top" priority, so add in reverse order of desired precedence?
    # Or just add them. Index 0 is checked first?
    # Actually, Index 0 is the highest priority rule in the list.
    
    requests.append(create_rule("HOT", GREEN, 0))
    requests.append(create_rule("WARM", YELLOW, 1))
    requests.append(create_rule("COLD", GREY, 2))
    requests.append(create_rule("NEUTRAL", GREY, 3))
    requests.append(create_rule("REMOVED", RED, 4))
    
    # We should probably clear old rules first?
    # deleteConditionalFormatRule? 
    # It's safer to just append new ones, or user might have others. 
    # But usually we want to manage our own.
    # Let's just add them.
    
    body = {'requests': requests}
    try:
        worksheet.spreadsheet.batch_update(body)
        print("  ✅ Formatting applied.")
    except Exception as e:
        print(f"  ❌ Failed to apply formatting: {e}")

def main():
    print(f"🚀 Analyzing Sentiment for {SHEET_NAME}...")
    
    sheets = GoogleSheetsClient(replies_sheet_name=SHEET_NAME)
    sheets.setup_sheets()
    worksheet = sheets.replies_sheet.sheet1
    
    raw_rows = worksheet.get_all_records()
    print(f"  🔍 Found {len(raw_rows)} total rows.")
    
    if not raw_rows:
        print("  ℹ️ Sheet is empty.")
        return
        
    clean_rows = []
    headers = ["Received At", "From Email", "From Name", "School Name", "Role", "Subject", "Snippet", "Sentiment", "Original Sender", "Original Subject", "Thread ID", "Action Taken", "Notes"]
    
    stats = {"HOT": 0, "WARM": 0, "COLD": 0, "NEUTRAL": 0, "REMOVED": 0, "WARMUP_FILTERED": 0}
    
    for row in raw_rows:
        subject = str(row.get("Subject", ""))
        snippet = str(row.get("Snippet", ""))
        sender = str(row.get("From Email", ""))
        
        full_text = f"{subject} {snippet} {sender}"
        
        # 1. Filter Warmup
        if is_warmup(full_text):
            stats["WARMUP_FILTERED"] += 1
            continue
            
        # 2. Analyze Sentiment
        # If sentiment is already manually set to something not "neutral", keep it?
        # User said "read all of them and re color them".
        # Let's overwrite "neutral" or empty, but maybe respect if we already classified?
        # Actually, let's re-classify everything to be safe/consistent.
        
        sentiment = classify_sentiment(full_text)
        row['Sentiment'] = sentiment
        stats[sentiment] += 1
        
        # Prepare for write-back
        row_list = [str(row.get(h, "")) for h in headers]
        clean_rows.append(row_list)
        
    print("  ✅ Analysis Complete:")
    for k, v in stats.items():
        print(f"    - {k}: {v}")
        
    # Write back
    print("  📝 Updating sheet content...")
    worksheet.clear()
    worksheet.update('A1', [headers] + clean_rows)
    
    # Apply Formatting
    apply_color_coding(worksheet)
    
    print("✨ Process Completed!")

if __name__ == "__main__":
    main()
