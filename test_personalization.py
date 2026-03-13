import os
import sys
import json
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.getcwd())

from Jobs.content.generator import generate_pitch

def test_personalization():
    load_dotenv()
    
    # Mock lead with deep website context
    lead = {
        "title": "Private School GA", # Generic title from Maps
        "address": "955 Peachtree Pkwy, Cumming, GA 30041",
        "phone": "(770) 888-4477",
        "email": "info@pinecrestacademy.org",
        "website_content": """
        Welcome to Pinecrest Academy. We are a private, Catholic, college-preparatory school 
        located in Cumming, GA, serving students from Pre-K through 12th Grade.
        
        Our mission is to form Christian leaders who will transform society. 
        Recent Highlights:
        - Our Varsity Soccer team recently won the GISA State Championship for the third year in a row!
        - Congratulations to our robotics team, 'The Cyber Knights', for their outstanding performance at the World Championships.
        - We are proud to announce our expansion into a new STEM-focused laboratory wing opening this Fall.
        - Offering 18+ Advanced Placement (AP) courses and a dual-enrollment partnership.
        
        Join us for our upcoming Open House on April 15th.
        """
    }
    
    print("\n--- TEST INPUT ---")
    print(f"Maps Title: {lead['title']}")
    print(f"Website Snippet: {lead['website_content'][:200].strip()}...")
    
    print("\n--- AI DRAFTING ---")
    school_name, email, sms = generate_pitch(lead)
    
    print("\n--- RESULTS ---")
    print(f"IDENTIFIED SCHOOL NAME: {school_name}")
    print("\n--- EMAIL ---")
    print(email)
    print("\n--- SMS ---")
    print(sms)
    print("\n--- END TEST ---")

if __name__ == "__main__":
    test_personalization()
