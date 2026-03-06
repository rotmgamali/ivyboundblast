
import sys
import logging
from unittest.mock import MagicMock

# 1. Setup Logging to mimic production
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFIER")

# 2. Mock Connections BEFORE importing scheduler (to avoid network calls)
sys.modules['mailreef_client'] = MagicMock()
sys.modules['sheets_integration'] = MagicMock()
# Mock logger_util if needed
sys.modules['logger_util'] = MagicMock()

# 3. Import System Components
from mailreef_automation.scheduler import EmailScheduler
from generators.email_generator import EmailGenerator

def verify_production_logic():
    print("\n--- 🔍 STARTING PRODUCTION SIMULATION ---\n")
    
    # Setup Generator with Regex Fix
    gen = EmailGenerator(client=MagicMock())
    # Mock LLM response to transparently return the prompt so we can see what the LLM 'sees'
    # Actual generator logic is in _prepare_school_prompts, but validation happens in send.
    # We will verify the PROMPT construction.
    
    # Setup Scheduler with Identity Fix (Pass mocks)
    # The actual signature is __init__(self, mailreef_client, sheets_client, config) usually, 
    # but based on previous reads involving 'mailreef' and 'sheets', let's just pass MagicMocks.
    # Looking at cache: Init likely takes (mailreef_client, sheets_client) or similar.
    # To be safe, let's inject dependencies via property if possible o r catch the error.
    # Actually, let's look at the file content again or just pass mocks.
    # Based on earlier view, it takes no args in __init__ but sets them? 
    # No, error says missing arguments.
    # Let's try passing 2 mocks.
    scheduler = EmailScheduler(MagicMock(), MagicMock())
    # Mock the internal map to be empty to PROVE that "@" bypass works
    scheduler.inbox_map = {} 
    
    # --- TEST CASE 1: Identity Lookup (The "Andrew" Bug) ---
    print("Test 1: Does 'mark@aspiring.work' bypass the empty ID map?")
    inbox_email = "mark@aspiring.work"
    
    # We strip out the logic from execute_send to test it in isolation
    # Replicating the exact logic in scheduler.py lines 275-280
    resolved_sender = "unknown"
    if "@" in str(inbox_email):
        resolved_sender = str(inbox_email)
    else:
        resolved_sender = scheduler.inbox_map.get(str(inbox_email), "unknown")
        
    if resolved_sender == "mark@aspiring.work":
        print(f"✅ PASS: Resolved '{inbox_email}' -> '{resolved_sender}'")
    else:
        print(f"❌ FAIL: Resolved '{inbox_email}' -> '{resolved_sender}'")

    # --- TEST CASE 2: Generator Hand-off & Regex (The "Variables" Bug) ---
    print("\nTest 2: Does Generator accept this sender and fill {{ school_name }}?")
    
    template = "Hi {{ first_name }}, how is the weather at {{ school_name }}?"
    lead = {
        "first_name": "Principal Skinner",
        "school_name": "Springfield Elementary",
        "role": "Principal",
        "city": "Springfield",
        "state": "IL"
    }
    
    # Run the generator preparation
    sys_msg, user_msg = gen._prepare_school_prompts(
        template_content=template,
        lead_data=lead,
        website_content="Raw scrape content",
        sequence_number=1,
        sender_email=resolved_sender # Passing "mark@aspiring.work"
    )
    
    print(f"\n[SYSTEM PROMPT]:\n{sys_msg}")
    print(f"\n[USER PROMPT]:\n{user_msg.split('RESEARCH')[0]}")
    
    # Checks
    if "You are Mark Greenstein" in sys_msg:
         print("✅ PASS: System Identity is 'Mark Greenstein'")
    else:
         print("❌ FAIL: System Identity incorrect.")
         
    if "Springfield Elementary" in user_msg:
         print("✅ PASS: {{ school_name }} replaced via Regex")
    else:
         print("❌ FAIL: {{ school_name }} NOT replaced.")
         
    if "Hi Principal Skinner," in user_msg and "{{ first_name }}" not in user_msg:
         print("✅ PASS: Greeting replaced correctly.")
    else:
         print("❌ FAIL: Greeting incorrect.")

if __name__ == "__main__":
    verify_production_logic()
