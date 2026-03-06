import sys
import os

# Mock the setup
class MockLead:
    def get(self, key, default=""):
        data = {
            "first_name": "Viva",  # Matches first word of school -> triggers sanitization
            "school_name": "Viva Christian Academy",
            "city": "Davie",
            "state": "FL",
            "role": "Principal"
        }
        return data.get(key, default)

def sanitize_name(name, lead_data):
    # Copy of the logic in email_generator.py
    if not name: return ""
    name = name.strip()
    lower_name = name.lower()
    
    # Blocklist
    blocklist = ["info", "admin", "office", "contact", "admissions", "principal", "head", "school"]
    if lower_name in blocklist:
        return ""
        
    # Check against School Name
    school_name = lead_data.get("school_name", "").lower()
    if school_name:
        school_parts = school_name.split()
        if school_parts and lower_name == school_parts[0]:
            print(f"DEBUG: Sanitized '{name}' because it matches first word of '{school_name}'")
            return ""
        if lower_name == school_name:
            return ""
            
    return name

def get_prompt():
    lead_data = MockLead()
    sanitized = sanitize_name(lead_data.get("first_name"), lead_data)
    
    if sanitized:
        first_name = sanitized
    else:
        first_name = "Good afternoon" # Simulated time greeting

    if first_name.startswith("Good "):
        greeting_line = f"{first_name},"
        template_instruction = f"IMPORTANT: Start the email with '{greeting_line}' exactly. Do NOT write 'Hi {first_name}'."
    else:
        greeting_line = f"Hi {first_name},"
        template_instruction = ""

    template_content = "Hi {{first_name}},\n\nI've been following..."

    prompt = f"""
    TEMPLATE:
    ---
    {template_content}
    ---

    INSTRUCTION: {template_instruction}
    If the template says "Hi {{first_name}}", replace it with "{greeting_line}".
    """
    
    print("\n--- GENERATED PROMPT SNIPPET ---")
    print(prompt)
    print("--------------------------------")

if __name__ == "__main__":
    get_prompt()
