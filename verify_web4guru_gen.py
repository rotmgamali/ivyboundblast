from generators.email_generator import EmailGenerator
from mailreef_automation.automation_config import CAMPAIGN_PROFILES
import json

def test_web4guru_gen():
    profile = CAMPAIGN_PROFILES["STRATEGY_B"]
    
    # Initialize Generator with Web4Guru settings
    generator = EmailGenerator(
        templates_dir=profile["templates_dir"],
        archetypes=profile["archetypes"],
        log_file=profile["log_file"]
    )
    
    # Mock Lead Data
    lead_data = {
        "email": "test@apple.com",
        "first_name": "Tim",
        "company_name": "Apple Inc.",
        "role": "Chief Executive Officer",
        "website": "apple.com"
    }
    
    print("\n🚀 Testing Web4Guru Generation (Archetype: Executive)")
    print("=" * 60)
    
    try:
        result = generator.generate_email(
            campaign_type="b2b",
            sequence_number=1,
            lead_data=lead_data,
            enrichment_data={} # Scrapes live
        )
        
        print(f"Subject: {result['subject']}")
        print("-" * 30)
        print(result['body'])
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_web4guru_gen()
