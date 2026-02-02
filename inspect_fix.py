
import sys
import os
import sqlite3

# Add project root path
sys.path.append(os.path.join(os.path.dirname(__file__), "mailreef_automation"))
sys.path.append(os.path.dirname(__file__))

from generators.email_generator import EmailGenerator

def inspect_fix():
    print("🔎 TESTING NAME SANITIZATION LOGIC")
    print("-" * 50)
    
    generator = EmailGenerator()
    
    # 1. Test Case: "Harvest" (Should be sanitized)
    lead_bad = {
        "first_name": "Harvest",
        "school_name": "Harvest Academy",
        "role": "Principal",
        "city": "Clewiston",
        "subtypes": "Christian",
        "domain": "harvestacademy.net"
    }
    
    print(f"INPUT: Name='{lead_bad['first_name']}', School='{lead_bad['school_name']}'")
    sanitized = generator._sanitize_name(lead_bad['first_name'], lead_bad)
    print(f"SANITIZER OUTPUT: '{sanitized}' (Expected: '')")
    
    # Run full generation prompt check (dry run)
    # We pass empty website content to force fallback behavior logic checks
    result = generator.generate_email("school", 1, lead_bad, {"website_content": ""})
    print("\n📩 GENERATED EMAIL BODY (extract):")
    print(result['body'][:200].replace('\n', ' '))
    
    if "Hi Harvest" in result['body']:
        print("\n❌ FAILURE: Still says 'Hi Harvest'")
    elif "Hi there" in result['body'] or "Hi Team" in result['body']:
        print("\n✅ SUCCESS: Used fallback 'Hi there'/'Hi Team'")
    else:
        print(f"\n⚠️ UNKNOWN RESULT: Check body above.")

    print("-" * 50)
    
    # 2. Test Case: "John" (Should stay)
    lead_good = {
        "first_name": "John",
        "school_name": "Harvest Academy",
        "role": "Principal"
    }
    print(f"INPUT: Name='{lead_good['first_name']}', School='{lead_good['school_name']}'")
    sanitized_good = generator._sanitize_name(lead_good['first_name'], lead_good)
    print(f"SANITIZER OUTPUT: '{sanitized_good}' (Expected: 'John')")
    
    if sanitized_good == "John":
        print("✅ SUCCESS: Kept valid name.")
    else:
        print("❌ FAILURE: Sanitized valid name.")

if __name__ == "__main__":
    inspect_fix()
