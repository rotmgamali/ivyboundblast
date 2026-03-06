import sys
import os
from generators.email_generator import EmailGenerator

# Verification checks
def run_verification():
    generator = EmailGenerator(client="mock") # Client won't be used for these checks
    
    print("--- 1. Testing 'Viva' Sanitization ---")
    lead_data = {
        "first_name": "Viva",
        "school_name": "Viva Christian Academy",
        "city": "Davie", 
        "state": "FL",
        "role": "Principal"
    }
    
    sanitized = generator._sanitize_name("Viva", lead_data)
    print(f"Input: Viva, School: Viva Christian Academy -> Output: '{sanitized}'")
    
    if sanitized == "Viva":
        print("✅ PASS: 'Viva' was preserved.")
    else:
        print(f"❌ FAIL: 'Viva' was sanitized to '{sanitized}'.")

    print("\n--- 2. Testing Double Greeting Prompt ---")
    # Force a time-based greeting by making sanitize return empty (simulating no name)
    # We can pass empty name
    lead_data_empty = {"first_name": "", "school_name": "Test School"}
    
    # We need to peek at _get_school_prompt but it's internal.
    # We'll call it directly.
    prompt = generator._get_school_prompt(
        template_content="Hi {{first_name}},\nBody...", 
        lead_data=lead_data_empty, 
        website_content="", 
        sequence_number=1
    )
    
    print("Checking prompt for forbidden instruction...")
    if "IMPORTANT: Start the email with" in prompt:
         print("❌ FAIL: Found the 'IMPORTANT' instruction that causes double greetings.")
    else:
         print("✅ PASS: The 'IMPORTANT' instruction is gone.")
         
    if "Replace \"Hi {{first_name}}\"" not in prompt and "Hi {{first_name}}" in prompt:
         # Wait, if we removed the instruction, we need to verify the replacement logic is still sound
         # Actually, the logic was: "If the template says Hi..., replace it..."
         # I need to check if I accidentally removed the *replacement* instruction too.
         # Looking at my edit, I removed 'template_instruction = ...'. 
         # I need to see if that variable was used later.
         pass

if __name__ == "__main__":
    run_verification()
