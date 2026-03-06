import sys
import os
# Add root to sys.path explicitly
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from generators.email_generator import EmailGenerator

def test_prompt_construction():
    print("Testing Prompt Logic...")
    
    # Mock dependencies
    generator = EmailGenerator(client=MagicMock())
    
    # Mock template file load
    generator._load_template_file = MagicMock(return_value="Hi {{first_name}},\n\nI noticed you are doing great things at {{school_name}}.")
    
    # Test Case 1: Valid Name
    lead_valid = {
        "first_name": "Andrew",
        "role": "Principal", 
        "school_name": "Ivy Academy",
        "city": "Boston",
        "state": "MA"
    }
    
    sys_prompt, user_prompt = generator._prepare_school_prompts(
        template_content="Hi {{first_name}},\n\nTest body.",
        lead_data=lead_valid,
        website_content="Specific research about robotics.",
        sequence_number=1,
        sender_email="mark@test.com"
    )
    
    print("\n--- TEST 1: Valid Name (Mark) ---")
    print(f"[SYSTEM]:\n{sys_prompt}")
    print(f"\n[USER]:\n{user_prompt}")
    
    if "Hi Andrew," in user_prompt:
        print("✅ SUCCESS: Python replaced {{first_name}} with 'Andrew'")
    else:
        print("❌ FAIL: Substitution missing")

    if "Hi {{first_name}}" in user_prompt:
         print("❌ FAIL: Placeholder still exists!")

    # Test Case 2: No Name (Time based)
    lead_empty = {
        "first_name": "",
        "role": "Admin",
        "school_name": "Generic School"
    }
    
    sys_prompt_2, user_prompt_2 = generator._prepare_school_prompts(
        template_content="Hi {{first_name}},\n\nTest body.",
        lead_data=lead_empty,
        website_content="",
        sequence_number=1,
        sender_email="andrew@test.com"
    )
    
    print("\n--- TEST 2: Empty Name (Time Fallback) ---")
    print(f"Greeting Line Used: {generator._get_time_greeting()}")
    print(f"\n[USER DRAFT excerpt]:\n{user_prompt_2.split('RESEARCH')[0]}")
    
    if "Hi {{first_name}}" in user_prompt_2:
        print("❌ FAIL: Placeholder still exists in fallback!")
    elif "Good " in user_prompt_2:
        print("✅ SUCCESS: Swapped to time-based greeting.")

if __name__ == "__main__":
    test_prompt_construction()
