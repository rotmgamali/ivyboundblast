import logging
from generators.email_generator import EmailGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def test_human_email():
    print("\n" + "="*60)
    print("TESTING HUMAN-FIRST PERSONALIZATION")
    print("="*60)
    
    generator = EmailGenerator()

    # Sample Lead: Catholic School Minister
    lead = {
        "first_name": "Father Michael",
        "role": "Campus Minister",
        "school_name": "St. Augustine Preparatory Academy",
        "city": "San Antonio",
        "state": "TX",
        "subtypes": "Catholic school, Private school",
        "domain": "staugustineprep.org",  # Dummy domain
        "description": "A Catholic college preparatory school committed to academic excellence and spiritual formation."
    }

    print("\n--- EMAIL 1 (Faith Leader) ---")
    result1 = generator.generate_email(
        campaign_type="school",
        sequence_number=1,
        lead_data=lead,
        enrichment_data={"website_content": "St. Augustine Prep is rooted in the Augustinian tradition of faith, community, and service. Our students participate in retreats, service projects, and daily prayer. We offer college prep courses and have a 98% college acceptance rate."}
    )
    
    print(f"\nSubject: {result1['subject']}")
    print("-" * 40)
    print(result1['body'])
    print("-" * 40)

    print("\n--- EMAIL 2 (Faith Leader) ---")
    result2 = generator.generate_email(
        campaign_type="school",
        sequence_number=2,
        lead_data=lead,
        enrichment_data={"website_content": "St. Augustine Prep is rooted in the Augustinian tradition of faith, community, and service. Our students participate in retreats, service projects, and daily prayer. We offer college prep courses and have a 98% college acceptance rate."}
    )
    
    print(f"\nSubject: {result2['subject']}")
    print("-" * 40)
    print(result2['body'])
    print("-" * 40)

if __name__ == "__main__":
    test_human_email()
