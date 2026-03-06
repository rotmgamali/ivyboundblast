from generators.email_generator import EmailGenerator
import logging

# Setup minimal logging to see the output
logging.basicConfig(level=logging.INFO)

def verify_cleanup():
    print("\n🚀 Verifying Greeting Fallback...")
    print("=" * 60)
    
    gen = EmailGenerator(log_file="verify_cleanup.log")
    
    # Test lead with "Administrator" name (now blocked)
    test_lead = {
        "email": "test@school.edu",
        "first_name": "Administrator",
        "school_name": "Cleanup High School",
        "role": "Principal",
        "domain": "school.edu"
    }
    
    # We'll mock the time greeting for testing if needed, 
    # but let's see what the generator does naturally.
    result = gen.generate_email(
        campaign_type="school",
        sequence_number=1,
        lead_data=test_lead,
        enrichment_data={"website_content": "We are a great school."}
    )
    
    body = result['body']
    print(f"Outcome Body Preview:\n{body[:100]}...")
    
    # Success condition: Body does NOT contain "Hi Administrator"
    if "Hi Administrator" in body:
        print("❌ FAILED: 'Hi Administrator' still present.")
    else:
        print("✅ SUCCESS: Greeting is clean (likely time-based or generic).")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    verify_cleanup()
