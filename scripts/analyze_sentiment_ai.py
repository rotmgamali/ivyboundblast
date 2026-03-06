import os
import sys
import json
import time
from datetime import datetime
from typing import List, Dict
import openai
from gspread.utils import a1_range_to_grid_range

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from sheets_integration import GoogleSheetsClient
import config

# --- CONFIGURATION ---
SHEET_NAME = "Ivy Bound - Reply Tracking"
MODEL_NAME = "gpt-4-turbo"  # Or "gpt-4o" if available to the key

SYSTEM_PROMPT = """You are an expert Sales Development Rep (SDR) for Ivy Bound, a premium education service provider. 
We send cold emails to School Principals and Administrators about "Boosting Enrollment", "Academic Outcomes", and "Test Prep".

Your goal is to classify the sentiment of a reply based on the text.

### Categories
1. **HOT**: Explicit interest. They want a call, meeting, details on pricing, or say "Yes".
   - Examples: "Let's chat", "What is the cost?", "Available Tuesday", "Yes taking new students".
2. **WARM**: Soft interest. They are not ready for a call but want info, or say "maybe later".
   - Examples: "Send me a brochure", "Reach out next semester", "Reviewing with board".
3. **COLD**: Not interested.
   - Examples: "Remove me", "Not interested", "We handle this in-house", "No thanks".
4. **REMOVED**: Hard bounce, wrong person, or aggressive refusal.
   - Examples: "Wrong email", "This person left", "Stop spamming".
5. **NEUTRAL**: Auto-replies that weren't filtered, referrals, or ambiguous/confusing responses.
   - Examples: "Out of office", "Contact X instead" (if referral, mark WARM usually, but if just passing the buck, NEUTRAL).

### Output Format
Return valid JSON only:
{
  "sentiment": "HOT" | "WARM" | "COLD" | "NEUTRAL" | "REMOVED",
  "reasoning": "Brief explanation (max 10 words)"
}
"""

def analyze_batch(replies: List[Dict]) -> List[Dict]:
    """Analyze a batch of replies using LLM."""
    
    # We can process one by one or generic batch. 
    # For 113 items, one by one is fine but slower. 
    # Let's do a loop with error handling.
    
    results = []
    
    client = openai.OpenAI(api_key=config.Config.OPENAI_API_KEY)
    
    print(f"  🤖 Processing {len(replies)} replies with {MODEL_NAME}...")
    
    for i, reply in enumerate(replies):
        snippet = reply.get("Entire Thread", "")
        subject = reply.get("Subject", "")
        body_text = f"Subject: {subject}\nBody: {snippet}"
        
        # Skip empty
        if len(body_text) < 10:
            results.append({"sentiment": "NEUTRAL", "reasoning": "Empty content"})
            continue
            
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Classify this reply:\n\n{body_text}"}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            results.append(data)
            
            # Simple progress log
            if (i+1) % 10 == 0:
                print(f"    - Analyzed {i+1}/{len(replies)}...")
                
        except Exception as e:
            print(f"    ❌ Error on item {i}: {e}")
            results.append({"sentiment": "NEUTRAL", "reasoning": "LLM Error"})
            
    return results

def apply_color_coding(worksheet):
    print("🎨 Applying Color Coding Rules...")
    
    # Define colors (RGB 0-1)
    GREEN = {'red': 0.85, 'green': 0.93, 'blue': 0.83}    # HOT
    YELLOW = {'red': 1.0, 'green': 0.95, 'blue': 0.8}     # WARM
    GREY = {'red': 0.9, 'green': 0.9, 'blue': 0.9}        # COLD / NEUTRAL
    RED = {'red': 0.96, 'green': 0.85, 'blue': 0.85}      # REMOVED
    
    # Column H is Sentiment (Index 7)
    # Range is A2:M1000 (assuming header is row 1)
    
    requests = []
    
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

    requests.append(create_rule("HOT", GREEN, 0))
    requests.append(create_rule("WARM", YELLOW, 1))
    requests.append(create_rule("COLD", GREY, 2))
    requests.append(create_rule("NEUTRAL", GREY, 3))
    requests.append(create_rule("REMOVED", RED, 4))
    
    body = {'requests': requests}
    try:
        # Clear old rules first? Not easily done without reading property id.
        # Just stacking them is usually okay.
        worksheet.spreadsheet.batch_update(body)
        print("  ✅ Formatting applied.")
    except Exception as e:
        print(f"  ❌ Failed to apply formatting: {e}")

def main():
    print(f"🚀 AI Sentiment Analysis for {SHEET_NAME}...")
    
    if not config.Config.OPENAI_API_KEY:
        print("❌ Error: OPENAI_API_KEY not found in config.")
        return

    sheets = GoogleSheetsClient(replies_sheet_name=SHEET_NAME)
    sheets.setup_sheets()
    worksheet = sheets.replies_sheet.sheet1
    
    raw_rows = worksheet.get_all_records()
    print(f"  🔍 Found {len(raw_rows)} total rows.")
    
    if not raw_rows:
        print("  ℹ️ Sheet is empty.")
        return

    # Analyze
    ai_results = analyze_batch(raw_rows)
    
    # Update rows locally
    clean_rows = []
    headers = ["Received At", "From Email", "From Name", "School Name", "Role", "Subject", "Entire Thread", "Sentiment", "Original Sender", "Original Subject", "Thread ID", "Action Taken", "Notes"]
    
    stats = {"HOT": 0, "WARM": 0, "COLD": 0, "NEUTRAL": 0, "REMOVED": 0}

    for i, row in enumerate(raw_rows):
        res = ai_results[i]
        
        row['Sentiment'] = res.get("sentiment", "NEUTRAL").upper()
        # Append reasoning to Notes
        # If Notes is empty, just set it. If exists, append.
        existing_notes = str(row.get("Notes", ""))
        reasoning = res.get("reasoning", "")
        
        # Avoid duplicate notes if re-running
        if reasoning and reasoning not in existing_notes:
            if existing_notes:
                row['Notes'] = f"{existing_notes} | AI: {reasoning}"
            else:
                row['Notes'] = f"AI: {reasoning}"
        
        stats[row['Sentiment']] += 1
        
        # Prepare for write-back
        row_list = [str(row.get(h, "")) for h in headers]
        clean_rows.append(row_list)
        
    # Sort Rows
    # Priority: HOT > WARM > NEUTRAL > COLD > REMOVED
    # Secondary: Date (Newest first? Or Oldest first? User said "most and least interested" which implies Sentiment. 
    # Usually "Earliest to Oldest" was previous request, but here let's do Sentiment (High->Low) then Date (Recent->Old).
    
    SENTIMENT_PRIORITY = {
        "HOT": 0,
        "WARM": 1,
        "NEUTRAL": 2,
        "COLD": 3,
        "REMOVED": 4
    }
    
    # helper to parse date
    def get_sort_key(row_list):
        # row_list is [Received At, From Email, ...]
        sentiment = row_list[7] # Index 7 is Sentiment
        date_str = row_list[0]
        try:
            dt = datetime.fromisoformat(date_str)
            ts = dt.timestamp()
        except:
            ts = 0
            
        prio = SENTIMENT_PRIORITY.get(sentiment, 5)
        # Sort by Prio (ASC), then Date (DESC - Newest First for interest)
        return (prio, -ts)

    clean_rows.sort(key=get_sort_key)

    print("  ✅ Analysis Complete & Sorted:")
    for k, v in stats.items():
        print(f"    - {k}: {v}")
        
    # Write back
    print("  📝 Updating sheet content...")
    worksheet.clear()
    worksheet.update('A1', [headers] + clean_rows)
    
    # Apply Formatting
    apply_color_coding(worksheet)
    
    print("✨ AI Analysis Completed!")

if __name__ == "__main__":
    main()
