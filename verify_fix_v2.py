import sys
import os
import logging

# Logic Fix: Ensure we can import from mailreef_automation
# This replicates the production environment where mailreef_automation is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
mailreef_path = os.path.join(current_dir, 'mailreef_automation')
sys.path.insert(0, mailreef_path)

# Now we can import EmailGenerator which imports logger_util
try:
    from generators.email_generator import EmailGenerator
except ImportError:
    # Fallback if generators is not in path (it adds itself, but the import needs to find IT first)
    # email_generator is in generators/ relative to root
    sys.path.append(current_dir)
    from generators.email_generator import EmailGenerator

def run_verification():
    print("--- 🔍 Verifying Personalization Logic ---")
    
    # Mock client
    generator = EmailGenerator(client="mock")
    
    # 1. Test "Viva" Sanitization
    print("\n1️⃣  Testing 'Viva' Sanitization")
    lead_data = {
        "first_name": "Viva",
        "school_name": "Viva Christian Academy",
        "city": "Davie", 
        "state": "FL",
        "role": "Principal"
    }
    
    sanitized = generator._sanitize_name("Viva", lead_data)
    print(f"   Input: 'Viva' (School: 'Viva Christian Academy')")
    print(f"   Output: '{sanitized}'")
    
    if sanitized == "Viva":
        print("   ✅ PASS: 'Viva' is allowed.")
    else:
        print(f"   ❌ FAIL: 'Viva' was sanitized to '{sanitized}'.")

    # 2. Test Double Greeting Prompt Instruction
    print("\n2️⃣  Testing Double Greeting Logic")
    # Simulate empty name fallback -> time greeting
    lead_data_empty = {"first_name": "", "school_name": "Test School"}
    
    # We need to test _get_school_prompt. 
    # The previous fix removed the explicitly "IMPORTANT" line.
    prompt = generator._get_school_prompt(
        template_content="Hi {{first_name}},\nBody...", 
        lead_data=lead_data_empty, 
        website_content="", 
        sequence_number=1
    )
    
    if "IMPORTANT: Start the email with" in prompt:
         print("   ❌ FAIL: Found the 'IMPORTANT' instruction (Causes Double Greeting).")
    else:
         print("   ✅ PASS: Prompt instruction is clean.")

    # 3. Test Sign-off Logic (Unit Test)
    print("\n3️⃣  Testing Sign-off Determination")
    
    # Case A: Mark
    mark_prompt = generator._get_school_prompt("...", {}, "", 1, sender_email="mark@ivybound.net")
    if "You are Mark Greenstein" in mark_prompt and "Sign off: Match the sender name Mark Greenstein" in mark_prompt:
        print("   ✅ PASS: 'mark@...' -> Mark Greenstein")
    else:
        print(f"   ❌ FAIL: 'mark@...' did not result in Mark Greenstein. Prompt excerpt: {mark_prompt[:100]}...")

    # Case B: Genelle
    genelle_prompt = generator._get_school_prompt("...", {}, "", 1, sender_email="genelle.ivybound@gmail.com")
    if "You are Genelle" in genelle_prompt:
        print("   ✅ PASS: 'genelle@...' -> Genelle")
    else:
        print("   ❌ FAIL: 'genelle@...' did not result in Genelle")

    # Case C: Unknown (Andrew)
    unknown_prompt = generator._get_school_prompt("...", {}, "", 1, sender_email="random@ivybound.net")
    if "You are Andrew" in unknown_prompt:
        print("   ✅ PASS: 'random@...' -> Andrew (Default)")
    else:
        print("   ❌ FAIL: Default fallback failed")

if __name__ == "__main__":
    run_verification()
