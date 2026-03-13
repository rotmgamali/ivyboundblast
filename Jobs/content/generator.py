import openai
import os
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

SYSTEM_PROMPT = """You are Andrew, a Director of Educational Partnerships at Ivybound. 
You are writing a ONE-TO-ONE email to a school administrator (Superintendents, Principals, or Academic Deans).

**1. EMAIL BODY INSTRUCTIONS:**
*   **Vibe:** Professional, consultative, and respectful of their time. "Building educational excellence together."
*   **Structure:**
    *   **Salutation:** "Hi [Name]," or "Dear [Title] [Last Name],"
    *   **The Hook:** Mention something specific about their institution from their website context (achievement, news). Do NOT use their school name in the hook.
    *   **The Pivot:** "I'm reaching out because Ivybound helps schools expand their course offerings (AP, electives, etc.) without the overhead of hiring new full-time staff. We share high-quality courses between partner schools."
    *   **The Value:** "Our model generates $50k-$150k in annual revenue for the school while serving more students."
    *   **The Ask:** "Would you be open to a 10-minute briefing on how this partnership could benefit your students?"
*   **Format:** Plain text. Professional subject line (e.g. "Expanding your course offerings" or "Partnership opportunity"). 4-5 sentences MAX.

**2. SMS SCRIPT INSTRUCTIONS (Use this EXACT Template):**
"Hi [Name], I'm Andrew from Ivybound. I sent you an email about our course-sharing partnership model that can help expand your curriculum while generating revenue. Would love to chat if you're interested? - Andrew"

Guidelines for SMS: 
* Keep it very brief and professional.
"""

def generate_pitch(business_data):
    """
    Generates email pitch AND sms follow-up.
    Returns tuple: (email_body, sms_script)
    """
    name = business_data.get("title", "Partner")
    website_text = business_data.get("website_content", "")
    email = business_data.get("email", "")
    has_email = "YES" if email and "@" in email else "NO"
    
    context = f"""
    Address: {business_data.get("address", "Utah")}
    Phone: {business_data.get("phone", "Unknown")}
    Has Valid Email: {has_email}
    Website Context: {website_text[:3500]}
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Write pitch & SMS for:\n{context}"}
            ],
            temperature=0.8
        )
        content = response.choices[0].message.content
        
        # Robust Parsing
        if "|||" in content:
            email, sms = content.split("|||", 1)
            return email.strip(), sms.strip()
        
        # Fallback 1: Look for "SMS Script:" label
        if "SMS Script:" in content:
            parts = content.split("SMS Script:", 1)
            return parts[0].strip(), parts[1].strip()

        # Fallback 2: Assume entire content is email, generate generic SMS
        print("   ⚠️ AI missed the separator. Using fallback SMS.")
        generic_sms = f"Hey {name.split()[0]}, I just sent you a quick email about streamlining your lead follow-up. Let me know if you got it? - Andrew"
        return content.strip(), generic_sms
    except Exception as e:
        print(f"❌ OpenAI Error: {e}")
        return "Hey, found your business and wanted to connect.", "Hey, found your business on Maps..."

def enrich_leads_with_pitch(leads):
    print("🧠 Generating hyper-personalized pitches (100k Offer)...")
    enriched = []
    for lead in leads:
        pitch = generate_pitch(lead)
        lead['generated_pitch'] = pitch
        enriched.append(lead)
        print(f"   > Pitch generated for {lead.get('title')}")
    return enriched
