import os
import sys
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.getcwd())

from generators.email_generator import EmailGenerator

def test_domain_guard():
    load_dotenv()
    gen = EmailGenerator()
    
    # 1. Test Case: Perfect Match
    print("\n✅ CASE 1: Perfect Match")
    lead1 = {
        "email": "principal@buckley.org",
        "website": "https://www.buckley.org/",
        "role": "Principal"
    }
    res1 = gen.generate_email("school", 1, lead1, {"website_content": "Welcome to The Buckley School..."})
    if res1.get("subject") != "SKIP_LEAD":
        print("RESULT: Verified (Expected)")
    else:
        print(f"RESULT: FAILED (Unexpected skip: {res1['body']})")

    # 2. Test Case: Generic Domain (Gmail) + AI Verification Success
    print("\n✅ CASE 2: Gmail + AI Context Success")
    lead2 = {
        "first_name": "Albus",
        "last_name": "Dumbledore",
        "email": "headmaster.hogwarts@gmail.com",
        "website": "https://www.hogwarts.edu/",
        "role": "Headmaster"
    }
    # Mocking website content that contains the name
    content2 = "Welcome to Hogwarts. Our Headmaster Albus Dumbledore oversees the Great Hall."
    res2 = gen.generate_email("school", 1, lead2, {"website_content": content2})
    if res2.get("subject") != "SKIP_LEAD":
        print(f"RESULT: Verified via AI (Expected)\nPreview: {res2['subject']}")
    else:
        print(f"RESULT: FAILED (Unexpected skip: {res2['body']})")

    # 3. Test Case: Outright Mismatch (Wrong School)
    print("\n✅ CASE 3: Outright Mismatch")
    lead3 = {
        "first_name": "John",
        "last_name": "Smith",
        "email": "john.smith@not-my-school.com",
        "website": "https://www.lakesideschool.org/",
        "role": "Principal"
    }
    # Content has no mention of John Smith
    content3 = "Lakeside School is a private school in Seattle. Our head is Kai Bynum."
    res3 = gen.generate_email("school", 1, lead3, {"website_content": content3})
    if res3.get("subject") == "SKIP_LEAD":
        print(f"RESULT: Successfully Blocked (Expected)\nReason: {res3['body']}")
    else:
        print("RESULT: FAILED (Allowed potentially wrong lead!)")

if __name__ == "__main__":
    test_domain_guard()
