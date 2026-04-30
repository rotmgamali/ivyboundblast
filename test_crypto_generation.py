#!/usr/bin/env python3
"""
Test the crypto email generation pipeline WITHOUT sending.
Generates personalized emails for sample contacts and prints them.
"""

import sys
import os

# Add paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "mailreef_automation"))

from generators.email_generator import EmailGenerator
from dotenv import load_dotenv

load_dotenv()

# Test contacts from the mega scraper results
TEST_LEADS = [
    {
        "email": "sponsordatadash@gmail.com",
        "first_name": "DataDash",
        "last_name": "",
        "role": "crypto analysis",
        "school_name": "DataDash",
        "website": "https://youtube.com/@DataDash",
        "city": "",
        "state": "",
        "custom_data": '{"source": "youtube about page", "platform": "youtube"}'
    },
    {
        "email": "brian@sfermion.io",
        "first_name": "Brian",
        "last_name": "",
        "role": "NFT/metaverse fund",
        "school_name": "Sfermion",
        "website": "https://sfermion.io",
        "city": "",
        "state": "",
        "custom_data": '{"source": "website contact page", "platform": "website"}'
    },
    {
        "email": "pitch@bitkraft.vc",
        "first_name": "Bitkraft",
        "last_name": "Ventures",
        "role": "gaming VC",
        "school_name": "Bitkraft Ventures",
        "website": "https://www.bitkraft.vc",
        "city": "",
        "state": "",
        "custom_data": '{"source": "website contact page", "platform": "website"}'
    },
    {
        "email": "hello@onbeam.com",
        "first_name": "Merit",
        "last_name": "Circle",
        "role": "gaming guild",
        "school_name": "Merit Circle",
        "website": "https://www.meritcircle.io",
        "city": "",
        "state": "",
        "custom_data": '{"source": "website contact page", "platform": "website"}'
    },
    {
        "email": "CryptoWendyO@protonmail.com",
        "first_name": "Wendy",
        "last_name": "O",
        "role": "crypto influencer",
        "school_name": "CryptoWendyO",
        "website": "https://youtube.com/@CryptoWendyO",
        "city": "",
        "state": "",
        "custom_data": '{"source": "youtube about page", "platform": "youtube"}'
    },
]

def main():
    print("=" * 70)
    print("  CRYPTO EMAIL GENERATION TEST")
    print("  Testing personalization pipeline without sending")
    print("=" * 70)

    # Create generator with crypto archetypes
    crypto_archetypes = {
        "influencer": ["influencer", "content creator", "youtuber", "streamer", "reviewer", "creator", "host", "podcaster"],
        "investor": ["vc", "venture", "capital", "fund", "investor", "investment", "partner", "analyst"],
        "promoter": ["marketing", "promotion", "pr", "media", "advertising", "agency", "growth", "shill", "caller", "alpha"],
        "general": ["general", "project", "protocol", "guild", "dao", "community"]
    }

    generator = EmailGenerator(
        templates_dir="templates/crypto",
        log_file="test_crypto.log",
        archetypes=crypto_archetypes
    )

    for i, lead in enumerate(TEST_LEADS):
        print(f"\n{'─' * 70}")
        print(f"  TEST {i+1}: {lead['first_name']} ({lead['role']})")
        print(f"  Email: {lead['email']}")
        print(f"  Website: {lead['website']}")
        print(f"{'─' * 70}")

        try:
            result = generator.generate_email(
                campaign_type="crypto",
                sequence_number=1,
                lead_data=lead,
                enrichment_data={},
                sender_email="andrew@demonsanddeities.com"
            )

            print(f"\n  SUBJECT: {result['subject']}")
            print(f"\n  BODY:")
            for line in result['body'].split('\n'):
                print(f"    {line}")

            # Word count
            body_words = len(result['body'].split())
            print(f"\n  Word count: {body_words}")

            if result['subject'] == "SKIP_LEAD":
                print("  ⚠️  LEAD WAS SKIPPED — check filters!")
            elif body_words > 100:
                print("  ⚠️  Too long — should be under 60 words body")
            else:
                print("  ✅  Looks good!")

        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 70}")
    print("  TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
